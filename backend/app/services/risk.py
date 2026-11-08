import math
from collections import deque
from app.config import RISK

VULNERABLE = {"pedestrian", "bicycle", "motorcycle"}


def severity_for(score):
    if score >= RISK["critical"]:
        return "CRITICAL"
    if score >= RISK["high"]:
        return "HIGH"
    if score >= RISK["moderate"]:
        return "MODERATE"
    return None


def warning_for(severity, cats):
    ped = " Pedestrian nearby." if "pedestrian" in cats else ""
    if severity == "CRITICAL":
        return "Warning. High collision risk. Slow down immediately." + ped
    if severity == "HIGH":
        return "High collision risk. Slow down and increase distance." + ped
    return "Maintain a safe distance." + ped


class RiskEngine:
    def __init__(self):
        self.tracks = {}     # id -> {"pos": deque, "speed": deque, "last": t}
        self.pair_gap = {}   # (a, b) -> deque of (t, gap)
        self.open = {}       # (a, b) -> latest event for that pair
        self.events = []

    # ---------- per-track motion ----------
    def _update_tracks(self, t, objs):
        for tid, o in objs.items():
            x1, y1, x2, y2 = o["bbox"]
            w = max(1.0, x2 - x1)
            tr = self.tracks.setdefault(
                tid, {"pos": deque(maxlen=12), "speed": deque(maxlen=60), "last": t})
            tr["last"] = t
            # foot point (bottom centre) approximates ground position
            tr["pos"].append((t, (x1 + x2) / 2, y2, w))
            if len(tr["pos"]) >= 5:
                p0, p1 = tr["pos"][-5], tr["pos"][-1]
                dt = p1[0] - p0[0]
                if dt > 0:
                    d = math.hypot(p1[1] - p0[1], p1[2] - p0[2])
                    avg_w = (p0[3] + p1[3]) / 2
                    tr["speed"].append((t, d / dt / avg_w))
        for tid in [k for k, v in self.tracks.items() if t - v["last"] > 3.0]:
            del self.tracks[tid]

    def _is_braking(self, tid):
        sp = self.tracks[tid]["speed"]
        if len(sp) < 10:
            return False
        t_now = sp[-1][0]
        recent = [v for t, v in sp if t_now - t <= 0.3]
        earlier = [v for t, v in sp if 0.6 <= t_now - t <= 1.3]
        if not recent or not earlier:
            return False
        r = sum(recent) / len(recent)
        e = sum(earlier) / len(earlier)
        return e >= RISK["brake_min_speed"] and r < RISK["brake_ratio"] * e

    # ---------- main update ----------
    def update(self, t, objs):
        """objs: {track_id: {"bbox": (x1,y1,x2,y2), "cat": str}}
        Returns list of (event, is_new)."""
        self._update_tracks(t, objs)
        ids = sorted(objs.keys())
        new_gap, out = {}, []

        for i in range(len(ids)):
            for j in range(i + 1, len(ids)):
                a, b = ids[i], ids[j]
                ca, cb = objs[a]["cat"], objs[b]["cat"]
                if ca == "pedestrian" and cb == "pedestrian":
                    continue
                ta, tb = self.tracks[a], self.tracks[b]
                if len(ta["pos"]) < 4 or len(tb["pos"]) < 4:
                    continue

                pa, pb = ta["pos"][-1], tb["pos"][-1]
                avg_w = (pa[3] + pb[3]) / 2
                gap = math.hypot(pa[1] - pb[1], pa[2] - pb[2]) / avg_w
                if gap > RISK["max_gap"]:
                    continue

                hist = self.pair_gap.get((a, b)) or deque(maxlen=8)
                hist.append((t, gap))
                new_gap[(a, b)] = hist
                if len(hist) < 4 or hist[-1][0] - hist[0][0] < 0.25:
                    continue

                # only alert when the gap is actually shrinking
                closing = (hist[0][1] - hist[-1][1]) / (hist[-1][0] - hist[0][0])
                if closing < RISK["min_closing"]:
                    continue
                ttc = gap / closing

                score, reasons = 0, []
                if gap < RISK["close_gap"]:
                    score += 30
                    reasons.append(f"very close ({gap:.1f} object-widths apart)")
                elif gap < RISK["near_gap"]:
                    score += 15
                    reasons.append(f"close ({gap:.1f} object-widths apart)")
                reasons.append(f"gap closing at {closing:.1f} object-widths/s")

                if ttc < RISK["ttc_critical"]:
                    score += 45
                elif ttc < RISK["ttc_high"]:
                    score += 30
                elif ttc < RISK["ttc_warn"]:
                    score += 15
                if ttc < RISK["ttc_warn"]:
                    reasons.append(
                        f"estimated time-to-collision about {ttc:.1f}s (uncalibrated estimate)")

                if closing >= RISK["fast_closing"]:
                    score += 10
                    reasons.append("fast approach")
                if (ca in VULNERABLE or cb in VULNERABLE) and gap < RISK["near_gap"]:
                    score += 10
                    reasons.append("vulnerable road user involved")
                braking = [x for x in (a, b) if self._is_braking(x)]
                if braking:
                    score += 15
                    reasons.append(f"sudden braking by #{braking[0]}")

                score = min(100, score)
                sev = severity_for(score)
                if sev is None:
                    continue
                out.append(self._register(
                    t, a, b, ca, cb, score, sev, ttc, closing, reasons))

        self.pair_gap = new_gap
        return out

    def _register(self, t, a, b, ca, cb, score, sev, ttc, closing, reasons):
        key = (a, b)
        ev = self.open.get(key)
        if ev and t - ev["last_t"] <= RISK["event_cooldown"]:
            ev["last_t"] = t
            if score > ev["score"]:  # keep the worst moment
                ev.update(
                    score=score, severity=sev,
                    peak_timestamp_sec=round(t, 2),
                    ttc_sec=round(ttc, 2),
                    reasons=reasons, reason_text="; ".join(reasons),
                    warning=warning_for(sev, (ca, cb)))
            return ev, False

        ev = {
            "event_id": len(self.events) + 1,
            "event_type": "predicted_collision_risk",
            "ids": [a, b],
            "categories": [ca, cb],
            "severity": sev,
            "score": score,
            "timestamp_sec": round(t, 2),
            "peak_timestamp_sec": round(t, 2),
            "ttc_sec": round(ttc, 2),
            "reasons": reasons,
            "reason_text": "; ".join(reasons),
            "warning": warning_for(sev, (ca, cb)),
            "snapshots": [],
            "last_t": t,
        }
        self.open[key] = ev
        self.events.append(ev)
        return ev, True

    def public_events(self):
        return [{k: v for k, v in e.items() if k != "last_t"} for e in self.events]