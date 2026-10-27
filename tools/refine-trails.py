"""Pull each trail's endpoints in to where the trail actually ends in the photograph.
usage: python refine-trails.py star-trails.webp trails.json   (rewrites trails.json in place)

extract-trails.py takes endpoints from its thresholded line-filter mask. The 15 px filter runs that mask
past each trail's end (median 3.7 px per end), and a mask that merges with a nearby blob can run much
further (one bright trail ended 22 px past the photo's). This walks the photo along each segment's axis
and moves each end inward to where the trail starts. It only ever shortens a segment.

Per segment, in the trails' canvas coordinates (pixel i spans [i, i+1], so the photo is sampled at -0.5):
  profile  brightest pixel within +-2 px of the axis, minus the darker of the two side backgrounds
           (means at 5-7 px either side), smoothed over 1 px, in 0.25 px steps from end a to end b.
  base     the same profile run on parallel lines 8-12 px off the axis (median), i.e. what the +-2 px
           max returns on bare sky. sigma is its MAD-based spread. Both are subtracted/used below.
  level    90th percentile of (profile - base) along the segment, the trail's own brightness.
  measured when level >= 6 grey levels and level >= 4 sigma.
  end      walking in from each end, the first point where (profile - base) reaches FRAC = 0.5 of level
           and stays there for RUN = 2 px, so a lone bright speck past the end does not stop the walk.
           Half of the trail's own brightness is where a drawn line's edge also sits.
  guard    a segment whose two ends would come within max(2 px, 20% of its length) of each other counts
           as unmeasured, so no segment inverts or collapses. A measured end may move in further than that
           (32 of the 2306 ends move more than 20 px, up to 173 px, where segments span two trails).
  fallback unmeasured (too faint) segments are shortened at each end by the median shortening of the
           measured ones, but by at most 40% of the length per end.
Run it once, on fresh extract-trails.py output: it is not idempotent (a second pass re-measures the shortened
segments and can trim merged ones further). Colour, peak and core width are left as they are, and the
output keeps extract-trails.py's format.
Some long segments are two parallel trails the extractor fused (a bright one and a dim one 3-6 px off);
those lose the dim stretch, since the canvas would otherwise draw it in the bright trail's colour."""
import sys, json, numpy as np
from PIL import Image
from scipy import ndimage as ndi

FRAC, RUN, MIN_LEVEL, MIN_SNR, MAX_SHRINK, STEP = 0.5, 2.0, 6.0, 4.0, 0.4, 0.25
src, path = sys.argv[1], sys.argv[2]
g = np.asarray(Image.open(src).convert('RGB')).astype(np.float32).mean(2)
data = json.load(open(path))

def profile(a, d, p, s, centre):
    def line(off):
        q = a[None] + s[:, None] * d + (centre + off) * p - 0.5
        return ndi.map_coordinates(g, [q[:, 1], q[:, 0]], order=1, mode='nearest')
    peak = np.max([line(o) for o in np.arange(-2, 2.01, 0.5)], 0)
    side = np.minimum(*[np.mean([line(k * o) for o in (5, 6, 7)], 0) for k in (1, -1)])
    return ndi.uniform_filter1d(peak - side, int(1 / STEP))

def first_run(above):
    """index where `above` first holds for RUN px straight, or None"""
    n = int(RUN / STEP)
    run = np.convolve(above.astype(int), np.ones(n, int), 'valid') == n
    return int(np.argmax(run)) if run.any() else None

def crossing(prof, s, i, thr, step):
    """sub-sample position where prof rises through thr just before index i (walking with `step`)"""
    j = i - step
    if j < 0 or j >= len(prof): return s[i]
    f = np.clip((thr - prof[j]) / max(prof[i] - prof[j], 1e-6), 0, 1)
    return s[j] + (s[i] - s[j]) * f

ends = []   # (shrink at a, shrink at b) or None if unmeasured
for seg in data['segs']:
    a = np.array(seg[:2], float); b = np.array(seg[2:4], float); L = float(np.hypot(*(b - a)))
    d = (b - a) / L; p = np.array([-d[1], d[0]]); s = np.arange(0, L + 1e-9, STEP)
    null = np.concatenate([profile(a, d, p, s, k * c) for k in (1, -1) for c in (8, 10, 12)])
    base = np.median(null); sigma = 1.4826 * np.median(np.abs(null - base))
    prof = profile(a, d, p, s, 0) - base
    level = np.percentile(prof, 90)
    if level < MIN_LEVEL or level < MIN_SNR * sigma: ends.append(None); continue
    thr = FRAC * level; above = prof >= thr
    i = first_run(above); k = first_run(above[::-1])
    if i is None or k is None: ends.append(None); continue
    sa = crossing(prof, s, i, thr, 1); k = len(s) - 1 - k
    sb = crossing(prof, s, k, thr, -1)
    if sb - sa < max(2.0, 0.2 * L): ends.append(None); continue
    ends.append((sa, L - sb))

fallback = float(np.median([e for pair in ends if pair for e in pair]))
before = [list(seg[:4]) for seg in data['segs']]
for seg, pair in zip(data['segs'], ends):
    a = np.array(seg[:2], float); b = np.array(seg[2:4], float); L = float(np.hypot(*(b - a))); d = (b - a) / L
    ka, kb = pair if pair else (min(fallback, MAX_SHRINK * L),) * 2
    na = a + d * max(ka, 0.0); nb = b - d * max(kb, 0.0)
    seg[:4] = [round(float(v), 1) for v in (*na, *nb)]
json.dump(data, open(path, 'w'), separators=(',', ':'))

cut = np.array([[np.hypot(o[0] - n[0], o[1] - n[1]), np.hypot(o[2] - n[2], o[3] - n[3])] for o, n in zip(before, (sg[:4] for sg in data['segs']))])
meas = np.array([e is not None for e in ends])
print(f'segments {len(ends)}: measured {meas.sum()}, fallback {(~meas).sum()} (shortened {fallback:.2f} px per end)')
print(f'changed {int((cut.max(1) > 0.05).sum())}; shortening per end (measured) median {np.median(cut[meas]):.2f}, '
      f'p10/p90 {np.percentile(cut[meas], 10):.2f}/{np.percentile(cut[meas], 90):.2f}, max {cut.max():.2f} px')
