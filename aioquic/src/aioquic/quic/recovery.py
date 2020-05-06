import math
import os
import time
from typing import Callable, Dict, Iterable, List, Optional

from .logger import QuicLoggerTrace
from .packet_builder import QuicDeliveryState, QuicSentPacket
from .rangeset import RangeSet

# loss detection
K_PACKET_THRESHOLD = 3
K_INITIAL_RTT = 0.5  # seconds
K_GRANULARITY = 0.001  # seconds
K_TIME_THRESHOLD = 9 / 8
K_MICRO_SECOND = 0.000001
K_SECOND = 1.0

# congestion control
K_MAX_DATAGRAM_SIZE = 1280
K_LOG_INTERVAL = 0.01
K_INITIAL_WINDOW = 10 * K_MAX_DATAGRAM_SIZE
K_MINIMUM_WINDOW = 2 * K_MAX_DATAGRAM_SIZE

# RENO
K_LOSS_REDUCTION_FACTOR = 0.5

# CUBIC
K_BETA_CUBIC = 0.7
K_WINDOW_AGGRESSIVENESS = 0.4

# VIVACE
K_THROUGHPUT_COEFF = 0.9
K_LATENCY_COEFF = 900
K_LOSS_COEFF = 11.35
K_LATENCY_FILTER = 0.01
K_EPSILON = 0.05
K_CONVERSION_FACTOR = 1
K_INITIAL_BOUNDARY = 0.05
K_BOUNDARY_INC = 0.1

def next_path(path_pattern):
    """
    Finds the next free path in an sequentially named list of files

    e.g. path_pattern = 'file-%s.txt':

    file-1.txt
    file-2.txt
    file-3.txt

    Runs in log(n) time where n is the number of existing files in sequence
    """
    i = 1

    # First do an exponential search
    while os.path.exists(path_pattern % i):
        i = i * 2

    # Result lies somewhere in the interval (i/2..i]
    # We call this interval (a..b] and narrow it down until a + 1 = b
    a, b = (i // 2, i)
    while a + 1 < b:
        c = (a + b) // 2 # interval midpoint
        a, b = (c, b) if os.path.exists(path_pattern % c) else (a, c)

    return path_pattern % b
class QuicPacketSpace:
    def __init__(self) -> None:
        self.ack_at: Optional[float] = None
        self.ack_queue = RangeSet()
        self.discarded = False
        self.expected_packet_number = 0
        self.largest_received_packet = -1
        self.largest_received_time: Optional[float] = None

        # sent packets and loss
        self.ack_eliciting_in_flight = 0
        self.largest_acked_packet = 0
        self.loss_time: Optional[float] = None
        self.sent_packets: Dict[int, QuicSentPacket] = {}


class QuicPacketPacer:
    def __init__(self) -> None:
        self.bucket_max: float = 0.0
        self.bucket_time: float = 0.0
        self.evaluation_time: float = 0.0
        self.packet_time: Optional[float] = None

    def next_send_time(self, now: float) -> float:
        if self.packet_time is not None:
            self.update_bucket(now=now)
            if self.bucket_time <= 0:
                return now + self.packet_time
        return None

    def update_after_send(self, now: float) -> None:
        if self.packet_time is not None:
            self.update_bucket(now=now)
            if self.bucket_time < self.packet_time:
                self.bucket_time = 0.0
            else:
                self.bucket_time -= self.packet_time

    def update_bucket(self, now: float) -> None:
        if now > self.evaluation_time:
            self.bucket_time = min(
                self.bucket_time + (now - self.evaluation_time), self.bucket_max
            )
            self.evaluation_time = now

    def update_rate(self, congestion_window: int, smoothed_rtt: float) -> None:
        pacing_rate = congestion_window / max(smoothed_rtt, K_MICRO_SECOND)
        self.packet_time = max(
            K_MICRO_SECOND, min(K_MAX_DATAGRAM_SIZE / pacing_rate, K_SECOND)
        )

        self.bucket_max = (
            max(
                2 * K_MAX_DATAGRAM_SIZE,
                min(congestion_window // 4, 16 * K_MAX_DATAGRAM_SIZE),
            )
            / pacing_rate
        )
        if self.bucket_time > self.bucket_max:
            self.bucket_time = self.bucket_max

class MonitorInterval:
    def __init__(self, rate: int, is_primary: bool) -> None:
        self.start_time: float = time.time()
        self.loss_count: int = 0
        self.sending_rate: int = rate // K_MAX_DATAGRAM_SIZE
        self.rtt_list: List[Tuple[float, float]] = []
        self.is_primary: bool = is_primary
        self.utility: float = 0

    def register_loss(self) -> None:
        self.loss_count += 1

    def register_rtt(self, rtt: float) -> None:
        self.rtt_list.append((time.time() - self.start_time, rtt))

    def compute_utility(self) -> None:
        # TODO: Compute rtt_diff as linear regression
        # drtt = (self.rtt_list[-1] - self.rtt_list[0]) / (time.time() - self.start_time)
        drtt = self._compute_rtt_slope()
        # print("Calculated Slope: %f" % drtt)
        self.utility = (math.pow(self.sending_rate, K_THROUGHPUT_COEFF)) - \
            (K_LATENCY_COEFF * self.sending_rate * drtt) - \
            (K_LOSS_COEFF * self.sending_rate * self.loss_count)

    def _compute_rtt_slope(self) -> float:
        n = len(self.rtt_list)
        if n > 2:
            sxy = sum(i[0] * i[1] for i in self.rtt_list)
            sx = sum(i[0] for i in self.rtt_list)
            sy = sum(i[1] for i in self.rtt_list)
            sx2 = sum(i[0] ** 2 for i in self.rtt_list)
            sy2 = sum(i[1] ** 2 for i in self.rtt_list)
            try:
                slope = ((n*sxy) - (sx*sy))/((n*sx2) - (sx**2))
            except e:
                printf(e)
                print("%d %f %f" % (n, sx2, sx))
                slope = 0
        elif n > 1:
            slope = (self.rtt_list[1][1] - self.rtt_list[0][1])/(self.rtt_list[1][0] - self.rtt_list[0][0])
        else:
            slope = 0
        if slope < K_LATENCY_FILTER:
            slope = 0
        return slope

class VivaceCongestionControl:
    """
    PCC Vivace congestion control.
    """

    def __init__(self, log: bool = False) -> None:
        self.bytes_in_flight = 0
        self.congestion_window = K_INITIAL_WINDOW
        self.mi_list: List[MonitorInterval] = [MonitorInterval(self.congestion_window, True)]
        self.positive_del: bool = False
        self.create_time = time.time()
        self.confidence_count: int = 0
        self._in_slow_start: bool = True
        self._rtt_monitor = QuicRttMonitor()
        self.change_boundary: float = K_INITIAL_BOUNDARY
        self.boundary_count: int = -1
        self.ssthresh: Optional[int] = None
        self._mi_duration: float = 0.1
        self.log = log
        self.loss_count = 0
        self.loss_size = 0

    def on_packet_acked(self, packet: QuicSentPacket, rtt: float) -> None:
        self.bytes_in_flight -= packet.sent_bytes

        current_mi = self.mi_list[-1]
        new_mi = None

        if time.time() > current_mi.start_time + self._mi_duration:
            # Current MI is finished, create new MI here
            current_mi.compute_utility()
            try:
                prev_mi = self.mi_list[-2]
                if self._in_slow_start and current_mi.utility < prev_mi.utility:
                    self._in_slow_start = False
            except:
                pass

            if self._in_slow_start:
                # slow start
                self.congestion_window *= 2
                # print("In slow start: %f" % current_mi.utility)
                new_mi = MonitorInterval(self.congestion_window, True)
            elif self.ssthresh is None:
                # slow start ended or mi with r ended
                # print("After r: %f" % current_mi.utility)
                self.ssthresh = self.congestion_window
                self.congestion_window = int(self.ssthresh * (1 + K_EPSILON))
                new_mi = MonitorInterval(self.congestion_window, True)
            elif current_mi.is_primary:
                # online learning with r(1+e) ended
                # print("After r(1+e): %f" % current_mi.utility)
                self.congestion_window = max(int(self.ssthresh * (1 - K_EPSILON)), K_MINIMUM_WINDOW)
                new_mi = MonitorInterval(self.congestion_window, False)
            else:
                # online learning with r(1-e) ended
                # print("After r(1-e): %f" % current_mi.utility)
                gamma = (prev_mi.utility - current_mi.utility) / (2 * self.ssthresh * K_EPSILON)
                confidence = self.confidence_amplifier(gamma)
                delta = (confidence * K_CONVERSION_FACTOR * gamma) * K_MAX_DATAGRAM_SIZE
                delta_dir = 1 if delta > 0 else -1
                if abs(delta) > (self.change_boundary * self.ssthresh):
                    delta = delta_dir * self.change_boundary * self.ssthresh
                else:
                    self.dynamic_boundary(delta)
                self.change_boundary = K_INITIAL_BOUNDARY + (self.boundary_count * K_BOUNDARY_INC)
                # print("delta: %f" % delta)
                self.congestion_window = max(int(self.ssthresh + delta), K_MINIMUM_WINDOW)
                new_mi = MonitorInterval(self.congestion_window, True)
                self.ssthresh = None

        if new_mi is not None:
            self.mi_list.append(new_mi)
            current_mi = new_mi

        current_mi.register_rtt(rtt)

    def on_packet_sent(self, packet: QuicSentPacket) -> None:
        self.bytes_in_flight += packet.sent_bytes

    def on_packets_expired(self, packets: Iterable[QuicSentPacket]) -> None:
        for packet in packets:
            self.bytes_in_flight -= packet.sent_bytes

    def on_packets_lost(self, packets: Iterable[QuicSentPacket], now: float) -> None:
        current_mi = self.mi_list[-1]

        for packet in packets:
            self.bytes_in_flight -= packet.sent_bytes
            self.loss_count += 1
            self.loss_size += packet.sent_bytes
            current_mi.register_loss()

        # TODO : collapse congestion window if persistent congestion

    def on_rtt_measurement(self, latest_rtt: float, now: float) -> None:
        # self._mi_duration = latest_rtt
        pass

    def dynamic_boundary(self, delta: float) -> None:
        w = K_INITIAL_BOUNDARY + (self.boundary_count * K_BOUNDARY_INC)
        while abs(delta) <= w * self.ssthresh:
            self.boundary_count -= 1
            w = K_INITIAL_BOUNDARY + (self.boundary_count * K_BOUNDARY_INC)
        self.boundary_count += 1

    def confidence_amplifier(self, gamma: float) -> float:
        current_del = gamma > 0
        if current_del == self.positive_del:
            self.confidence_count += 1
            self.boundary_count += 1
        else:
            self.positive_del = current_del
            self.confidence_count = 1
            self.boundary_count = 0

        if self.confidence_count <= 3:
            ans = self.confidence_count
        else:
            ans = (2 * self.confidence_count) - 3
        return ans

class CubicCongestionControl:
    """
    CUBIC congestion control.
    """

    def __init__(self, log: bool = False) -> None:
        self.bytes_in_flight = 0
        self.congestion_window = K_INITIAL_WINDOW
        self._congestion_recovery_start_time = 0.0
        self._rtt_monitor = QuicRttMonitor()
        self._w_max = 0
        self._w_last_max = 0
        self.congestion_avoidance_start_time: Optional[float] = None
        self.create_time: float = time.time()
        self.ssthresh: Optional[int] = None
        self.log = log
        self.loss_count = 0
        self.loss_size = 0
        self._loss_stash = 0
        self._loss_thresh = 10
        self._should_decrease = False

    def on_packet_acked(self, packet: QuicSentPacket, rtt: float) -> None:
        self.bytes_in_flight -= packet.sent_bytes

        # don't increase window in congestion recovery
        if packet.sent_time <= self._congestion_recovery_start_time:
            return

        if self.ssthresh is None or self.congestion_window < self.ssthresh:
            # slow start
            self.congestion_window += packet.sent_bytes
        else:
            # congestion avoidance
            if self.congestion_avoidance_start_time is None:
                self.congestion_avoidance_start_time = time.time()

            elapsed_time = time.time() - self.congestion_avoidance_start_time

            # Optional TCP Standard Region [Skipped]
            # w_est = self._get_standard_estimate(elapsed_time, rtt)
            # w_cubic = self._get_cubic_window_size(elapsed_time)
            # if w_cubic < w_est:
            #     # Friendly Region
            #     self.avoidance_mode = 'FR'
            #     self.congestion_window = int(w_est)
            # else:
            cubic_wnd = self._get_cubic_window_size(elapsed_time + rtt)
            cwnd = self.congestion_window // K_MAX_DATAGRAM_SIZE
            delta = ((cubic_wnd - cwnd) / cwnd) * K_MAX_DATAGRAM_SIZE
            # print("{0} {1} {2}".format(cubic_wnd, cwnd, delta))
            self.congestion_window += int(delta)


    def on_packet_sent(self, packet: QuicSentPacket) -> None:
        self.bytes_in_flight += packet.sent_bytes

    def on_packets_expired(self, packets: Iterable[QuicSentPacket]) -> None:
        for packet in packets:
            self.bytes_in_flight -= packet.sent_bytes

    def on_packets_lost(self, packets: Iterable[QuicSentPacket], now: float) -> None:
        lost_largest_time = 0.0
        for packet in packets:
            self.bytes_in_flight -= packet.sent_bytes
            self.loss_count += 1
            self.loss_size += packet.sent_bytes
            lost_largest_time = packet.sent_time

        if self.ssthresh is None:
            self._should_decrease = True
        elif len(packets) > self._loss_thresh:
            self._should_decrease = True
            self._loss_thresh = math.ceil(1.25 * self._loss_thresh)
        else:
            self._loss_stash += len(packets)
            if self._loss_stash > int(1.5 * self._loss_thresh):
                self._should_decrease = True
                self._loss_stash %= int(1.5 * self._loss_thresh)
            else:
                self._loss_thresh = math.ceil(0.75 * self._loss_thresh)
                self._should_decrease = False

        # start a new congestion event if packet was sent after the
        # start of the previous congestion recovery period.
        if lost_largest_time > self._congestion_recovery_start_time and self._should_decrease:
            self._congestion_recovery_start_time = now
            self._w_max = self.congestion_window // K_MAX_DATAGRAM_SIZE
            if self._w_max < (0.95 * self._w_last_max):
                self._w_last_max = self._w_max
                self._w_max = int (self._w_max * (1 + K_BETA_CUBIC) / 2)
            else:
                self._w_last_max = self._w_max
            self.congestion_window = max(int(self.congestion_window * K_BETA_CUBIC), K_MINIMUM_WINDOW)
            self.ssthresh = self.congestion_window
            self.congestion_avoidance_start_time = None

        # TODO : collapse congestion window if persistent congestion

    def on_rtt_measurement(self, latest_rtt: float, now: float) -> None:
        pass

    def _get_cubic_window_size(self, time: float) -> float:
        K = math.pow(self._w_max * (1 - K_BETA_CUBIC) / K_WINDOW_AGGRESSIVENESS, 1/3)
        w_cubic = K_WINDOW_AGGRESSIVENESS * math.pow((time - K), 3) + self._w_max
        return w_cubic

    def _get_standard_estimate(self, t: float, rtt: float) -> float:
        try:
            w_est = self._w_max * K_BETA_CUBIC + (3 * (1 - K_BETA_CUBIC) / (1 + K_BETA_CUBIC)) * (t/rtt)
        except:
            w_est = K_MINIMUM_WINDOW
        return w_est

class RenoCongestionControl:
    """
    New Reno congestion control.
    """

    def __init__(self, log: bool = False) -> None:
        self.bytes_in_flight = 0
        self.congestion_window = K_INITIAL_WINDOW
        self._congestion_recovery_start_time = 0.0
        self._congestion_stash = 0
        self._rtt_monitor = QuicRttMonitor()
        self.create_time = time.time()
        self.ssthresh: Optional[int] = None
        self.log = log
        self.loss_count = 0
        self.loss_size = 0

    def on_packet_acked(self, packet: QuicSentPacket, rtt: float) -> None:
        self.bytes_in_flight -= packet.sent_bytes

        # don't increase window in congestion recovery
        if packet.sent_time <= self._congestion_recovery_start_time:
            return

        if self.ssthresh is None or self.congestion_window < self.ssthresh:
            # slow start
            self.congestion_window += packet.sent_bytes
        else:
            # congestion avoidance
            self._congestion_stash += packet.sent_bytes
            count = self._congestion_stash // self.congestion_window
            if count:
                self._congestion_stash -= count * self.congestion_window
                self.congestion_window += count * K_MAX_DATAGRAM_SIZE

    def on_packet_sent(self, packet: QuicSentPacket) -> None:
        self.bytes_in_flight += packet.sent_bytes

    def on_packets_expired(self, packets: Iterable[QuicSentPacket]) -> None:
        for packet in packets:
            self.bytes_in_flight -= packet.sent_bytes

    def on_packets_lost(self, packets: Iterable[QuicSentPacket], now: float) -> None:
        lost_largest_time = 0.0
        for packet in packets:
            self.bytes_in_flight -= packet.sent_bytes
            self.loss_count += 1
            self.loss_size += packet.sent_bytes
            lost_largest_time = packet.sent_time

        # start a new congestion event if packet was sent after the
        # start of the previous congestion recovery period.
        if lost_largest_time > self._congestion_recovery_start_time:
            self._congestion_recovery_start_time = now
            self.congestion_window = max(
                int(self.congestion_window * K_LOSS_REDUCTION_FACTOR), K_MINIMUM_WINDOW
            )
            self.ssthresh = self.congestion_window

        # TODO : collapse congestion window if persistent congestion

    def on_rtt_measurement(self, latest_rtt: float, now: float) -> None:
        # check whether we should exit slow start
        if self.ssthresh is None and self._rtt_monitor.is_rtt_increasing(
            latest_rtt, now
        ):
            self.ssthresh = self.congestion_window


class QuicPacketRecovery:
    """
    Packet loss and congestion controller.
    """

    def __init__(
        self,
        is_client_without_1rtt: bool,
        send_probe: Callable[[], None],
        quic_logger: Optional[QuicLoggerTrace] = None,
        congestion_controller: Optional[int] = 0,
        should_log: Optional[bool] = True,
    ) -> None:
        self.max_ack_delay = 0.025
        self.spaces: List[QuicPacketSpace] = []

        # callbacks
        self._quic_logger = quic_logger
        self._send_probe = send_probe

        # loss detection
        self._pto_count = 0
        self._rtt_initialized = False
        self._rtt_latest = 0.0
        self._rtt_min = math.inf
        self._rtt_smoothed = 0.0
        self._rtt_variance = 0.0
        self._time_of_last_sent_ack_eliciting_packet = 0.0

        # congestion control
        self._should_log = should_log
        congestion_switcher = {
            0: RenoCongestionControl(self._should_log),
            1: CubicCongestionControl(self._should_log),
            2: VivaceCongestionControl(self._should_log)
        }
        self._cc = congestion_switcher.get(congestion_controller, RenoCongestionControl(self._should_log))
        self._pacer = QuicPacketPacer()

        if isinstance(self._cc, RenoCongestionControl):
            log_file_dir = 'logs/reno/'
        elif isinstance(self._cc, CubicCongestionControl):
            log_file_dir = 'logs/cubic/'
        elif isinstance(self._cc, VivaceCongestionControl):
            log_file_dir = 'logs/vivace/'

        self.is_client_without_1rtt = is_client_without_1rtt
        if self.is_client_without_1rtt:
            log_file_dir = next_path(log_file_dir + 'client/c%s/')
        else:
            log_file_dir = next_path(log_file_dir + 'server/s%s/')

        try:
            os.makedirs(log_file_dir)
        except FileExistsError:
            # directory already exists
            pass

        self._last_throughput_log_time = 0
        self._last_latency_log_time = 0
        self._last_loss_log_time = 0

        try:
            self._throughput_log_file = open(log_file_dir + 'window.log', 'w')
            self._latency_log_file = open(log_file_dir + 'latency.log', 'w')
            self._loss_log_file = open(log_file_dir + 'loss.log', 'w')
        except Exception as e:
            print(e)

    def __del__(self):
        if self._throughput_log_file is not None:
            self._throughput_log_file.close()
        if self._loss_log_file is not None:
            self._loss_log_file.close()
        if self._latency_log_file is not None:
            self._latency_log_file.close()

    @property
    def bytes_in_flight(self) -> int:
        return self._cc.bytes_in_flight

    @property
    def congestion_window(self) -> int:
        return self._cc.congestion_window

    def discard_space(self, space: QuicPacketSpace) -> None:
        assert space in self.spaces

        self._cc.on_packets_expired(
            filter(lambda x: x.in_flight, space.sent_packets.values())
        )
        space.sent_packets.clear()

        space.ack_at = None
        space.ack_eliciting_in_flight = 0
        space.loss_time = None

        if self._quic_logger is not None:
            self._log_metrics_updated()

    def get_earliest_loss_space(self) -> Optional[QuicPacketSpace]:
        loss_space = None
        for space in self.spaces:
            if space.loss_time is not None and (
                loss_space is None or space.loss_time < loss_space.loss_time
            ):
                loss_space = space
        return loss_space

    def get_loss_detection_time(self) -> float:
        # loss timer
        loss_space = self.get_earliest_loss_space()
        if loss_space is not None:
            return loss_space.loss_time

        # packet timer
        if (
            self.is_client_without_1rtt
            or sum(space.ack_eliciting_in_flight for space in self.spaces) > 0
        ):
            if not self._rtt_initialized:
                timeout = 2 * K_INITIAL_RTT * (2 ** self._pto_count)
            else:
                timeout = self.get_probe_timeout() * (2 ** self._pto_count)
            return self._time_of_last_sent_ack_eliciting_packet + timeout

        return None

    def get_probe_timeout(self) -> float:
        return (
            self._rtt_smoothed
            + max(4 * self._rtt_variance, K_GRANULARITY)
            + self.max_ack_delay
        )

    def on_ack_received(
        self,
        space: QuicPacketSpace,
        ack_rangeset: RangeSet,
        ack_delay: float,
        now: float,
    ) -> None:
        """
        Update metrics as the result of an ACK being received.
        """
        is_ack_eliciting = False
        largest_acked = ack_rangeset.bounds().stop - 1
        largest_newly_acked = None
        largest_sent_time = None

        if largest_acked > space.largest_acked_packet:
            space.largest_acked_packet = largest_acked

        for packet_number in sorted(space.sent_packets.keys()):
            if packet_number > largest_acked:
                break
            if packet_number in ack_rangeset:
                # remove packet and update counters
                packet = space.sent_packets.pop(packet_number)
                if packet.is_ack_eliciting:
                    is_ack_eliciting = True
                    space.ack_eliciting_in_flight -= 1
                if packet.in_flight:
                    if isinstance(self._cc, VivaceCongestionControl):
                        self._cc.on_packet_acked(packet, now - packet.sent_time)
                    else:
                        self._cc.on_packet_acked(packet, self._rtt_smoothed)
                    self._log_window_size("ACK")
                largest_newly_acked = packet_number
                largest_sent_time = packet.sent_time

                # trigger callbacks
                for handler, args in packet.delivery_handlers:
                    handler(QuicDeliveryState.ACKED, *args)

        # nothing to do if there are no newly acked packets
        if largest_newly_acked is None:
            return

        if largest_acked == largest_newly_acked and is_ack_eliciting:
            latest_rtt = now - largest_sent_time
            log_rtt = True

            # limit ACK delay to max_ack_delay
            ack_delay = min(ack_delay, self.max_ack_delay)

            # update RTT estimate, which cannot be < 1 ms
            self._rtt_latest = max(latest_rtt, 0.001)
            if self._rtt_latest < self._rtt_min:
                self._rtt_min = self._rtt_latest
            if self._rtt_latest > self._rtt_min + ack_delay:
                self._rtt_latest -= ack_delay

            if not self._rtt_initialized:
                self._rtt_initialized = True
                self._rtt_variance = latest_rtt / 2
                self._rtt_smoothed = latest_rtt
            else:
                self._rtt_variance = 3 / 4 * self._rtt_variance + 1 / 4 * abs(
                    self._rtt_min - self._rtt_latest
                )
                self._rtt_smoothed = (
                    7 / 8 * self._rtt_smoothed + 1 / 8 * self._rtt_latest
                )

            # inform congestion controller
            if isinstance(self._cc, VivaceCongestionControl):
                self._cc.on_rtt_measurement(self._rtt_latest, now=now)
            else:
                self._cc.on_rtt_measurement(self._rtt_smoothed, now=now)
            self._log_network_latency(self._rtt_latest, self._rtt_smoothed)
            self._pacer.update_rate(
                congestion_window=self._cc.congestion_window,
                smoothed_rtt=self._rtt_smoothed,
            )

        else:
            log_rtt = False

        self._detect_loss(space, now=now)

        if self._quic_logger is not None:
            self._log_metrics_updated(log_rtt=log_rtt)

        self._pto_count = 0

    def on_loss_detection_timeout(self, now: float) -> None:
        loss_space = self.get_earliest_loss_space()
        if loss_space is not None:
            self._detect_loss(loss_space, now=now)
        else:
            self._pto_count += 1

            # reschedule some data
            for space in self.spaces:
                self._on_packets_lost(
                    tuple(
                        filter(
                            lambda i: i.is_crypto_packet, space.sent_packets.values()
                        )
                    ),
                    space=space,
                    now=now,
                )

            self._send_probe()

    def on_packet_sent(self, packet: QuicSentPacket, space: QuicPacketSpace) -> None:
        space.sent_packets[packet.packet_number] = packet

        if packet.is_ack_eliciting:
            space.ack_eliciting_in_flight += 1
        if packet.in_flight:
            if packet.is_ack_eliciting:
                self._time_of_last_sent_ack_eliciting_packet = packet.sent_time

            # add packet to bytes in flight
            self._cc.on_packet_sent(packet)

            if self._quic_logger is not None:
                self._log_metrics_updated()

    def _detect_loss(self, space: QuicPacketSpace, now: float) -> None:
        """
        Check whether any packets should be declared lost.
        """
        loss_delay = K_TIME_THRESHOLD * (
            max(self._rtt_latest, self._rtt_smoothed)
            if self._rtt_initialized
            else K_INITIAL_RTT
        )
        packet_threshold = space.largest_acked_packet - K_PACKET_THRESHOLD
        time_threshold = now - loss_delay

        lost_packets = []
        space.loss_time = None
        for packet_number, packet in space.sent_packets.items():
            if packet_number > space.largest_acked_packet:
                break

            if packet_number <= packet_threshold or packet.sent_time <= time_threshold:
                lost_packets.append(packet)
            else:
                packet_loss_time = packet.sent_time + loss_delay
                if space.loss_time is None or space.loss_time > packet_loss_time:
                    space.loss_time = packet_loss_time

        self._on_packets_lost(lost_packets, space=space, now=now)

    def _log_metrics_updated(self, log_rtt=False) -> None:
        data = {
            "bytes_in_flight": self._cc.bytes_in_flight,
            "cwnd": self._cc.congestion_window,
        }
        if self._cc.ssthresh is not None:
            data["ssthresh"] = self._cc.ssthresh

        if log_rtt:
            data.update(
                {
                    "latest_rtt": self._quic_logger.encode_time(self._rtt_latest),
                    "min_rtt": self._quic_logger.encode_time(self._rtt_min),
                    "smoothed_rtt": self._quic_logger.encode_time(self._rtt_smoothed),
                    "rtt_variance": self._quic_logger.encode_time(self._rtt_variance),
                }
            )

        self._quic_logger.log_event(
            category="recovery", event="metrics_updated", data=data
        )

    def _on_packets_lost(
        self, packets: Iterable[QuicSentPacket], space: QuicPacketSpace, now: float
    ) -> None:
        lost_packets_cc = []
        for packet in packets:
            del space.sent_packets[packet.packet_number]

            if packet.in_flight:
                lost_packets_cc.append(packet)

            if packet.is_ack_eliciting:
                space.ack_eliciting_in_flight -= 1

            if self._quic_logger is not None:
                self._quic_logger.log_event(
                    category="recovery",
                    event="packet_lost",
                    data={
                        "type": self._quic_logger.packet_type(packet.packet_type),
                        "packet_number": str(packet.packet_number),
                    },
                )
                self._log_metrics_updated()

            # trigger callbacks
            for handler, args in packet.delivery_handlers:
                handler(QuicDeliveryState.LOST, *args)

        # inform congestion controller
        if lost_packets_cc:
            self._cc.on_packets_lost(lost_packets_cc, now=now)
            self._log_window_size("LOSS")
            self._log_packet_loss()
            self._pacer.update_rate(
                congestion_window=self._cc.congestion_window,
                smoothed_rtt=self._rtt_smoothed,
            )
            if self._quic_logger is not None:
                self._log_metrics_updated()

    def _log_window_size(self, reason: str) -> None:
        if self._cc.log:
            if time.time() - self._last_throughput_log_time > K_LOG_INTERVAL:
                self._throughput_log_file.write("{0} {1}\n"
                .format(self._cc.congestion_window, time.time() - self._cc.create_time))
                self._last_throughput_log_time = time.time()

    def _log_packet_loss(self) -> None:
        if self._cc.log:
            if time.time() - self._last_loss_log_time > K_LOG_INTERVAL:
                self._loss_log_file.write("{0} {1} {2}\n"
                .format(self._cc.loss_count, self._cc.loss_size, time.time() - self._cc.create_time))
                self._last_latency_log_time = time.time()

    def _log_network_latency(self, latest: float, smoothed: float) -> None:
        if self._cc.log:
            if time.time() - self._last_latency_log_time > K_LOG_INTERVAL:
                self._latency_log_file.write("{0} {1} {2}\n"
                .format(latest, smoothed, time.time() - self._cc.create_time))
                self._last_latency_log_time = time.time()

class QuicRttMonitor:
    """
    Roundtrip time monitor for HyStart.
    """

    def __init__(self) -> None:
        self._increases = 0
        self._last_time = None
        self._ready = False
        self._size = 5

        self._filtered_min: Optional[float] = None

        self._sample_idx = 0
        self._sample_max: Optional[float] = None
        self._sample_min: Optional[float] = None
        self._sample_time = 0.0
        self._samples = [0.0 for i in range(self._size)]

    def add_rtt(self, rtt: float) -> None:
        self._samples[self._sample_idx] = rtt
        self._sample_idx += 1

        if self._sample_idx >= self._size:
            self._sample_idx = 0
            self._ready = True

        if self._ready:
            self._sample_max = self._samples[0]
            self._sample_min = self._samples[0]
            for sample in self._samples[1:]:
                if sample < self._sample_min:
                    self._sample_min = sample
                elif sample > self._sample_max:
                    self._sample_max = sample

    def is_rtt_increasing(self, rtt: float, now: float) -> bool:
        if now > self._sample_time + K_GRANULARITY:
            self.add_rtt(rtt)
            self._sample_time = now

            if self._ready:
                if self._filtered_min is None or self._filtered_min > self._sample_max:
                    self._filtered_min = self._sample_max

                delta = self._sample_min - self._filtered_min
                if delta * 4 >= self._filtered_min:
                    self._increases += 1
                    if self._increases >= self._size:
                        return True
                elif delta > 0:
                    self._increases = 0
        return False
