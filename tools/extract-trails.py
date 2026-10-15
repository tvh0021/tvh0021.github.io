"""Measure the star trails in a long-exposure photo and build the layers for the web animation.
Outputs: plate.png (sky with trails removed), trees.png (tree silhouettes with alpha),
trails.json ({w, h, segs: [x0, y0, x1, y1, [r, g, b], peak, core_width]})."""
import sys, json, numpy as np
from PIL import Image, ImageDraw
from scipy import ndimage as ndi
src, out, thr = sys.argv[1], sys.argv[2], float(sys.argv[3])
im = np.asarray(Image.open(src).convert('RGB')).astype(np.float32)
H, W = im.shape[:2]; g = im.mean(2)

def kernel(theta, offset, L=15, size=31):
    d = np.array([np.cos(theta), np.sin(theta)]); p = np.array([-d[1], d[0]])
    k = np.zeros((size, size), np.float32); c = size // 2
    for t in np.linspace(-L / 2, L / 2, L * 3):
        k[int(round(c + d[1] * t + p[1] * offset)), int(round(c + d[0] * t + p[0] * offset))] = 1
    return k / k.sum()

# line filter bank across the range of trail angles in this frame
resp = np.full(g.shape, -1e9, np.float32)
for deg in np.arange(110, 142, 2):
    th = np.radians(deg)
    r = ndi.convolve(g, kernel(th, 0)) - np.minimum(ndi.convolve(g, kernel(th, 5)), ndi.convolve(g, kernel(th, -5)))
    resp = np.maximum(resp, r)
B_ = 8
resp[:B_] = resp[-B_:] = 0; resp[:, :B_] = resp[:, -B_:] = 0   # dark border stripe in the photo
mask = resp > thr

# tree silhouettes: darker than a smooth sky estimate
sky = ndi.median_filter(ndi.zoom(g, 0.125, order=1), size=9)
sky = ndi.zoom(sky, (H / sky.shape[0], W / sky.shape[1]), order=1)[:H, :W]
tree_a = np.clip((sky - g - 4) / 10, 0, 1); tree_a[: int(H * 0.5)] = 0
tree = tree_a > 0.05

def measure(ys, xs):
    w8 = resp[ys, xs]
    pts = np.stack([xs, ys], 1).astype(float); c = (pts * w8[:, None]).sum(0) / w8.sum()
    _, _, vt = np.linalg.svd((pts - c) * np.sqrt(w8)[:, None], full_matrices=False)
    d = vt[0]; p = np.array([-d[1], d[0]])
    along = (pts - c) @ d; across = (pts - c) @ p
    L = along.max() - along.min(); wid = np.percentile(np.abs(across), 95) * 2 + 1
    ang = np.degrees(np.arctan2(d[1], d[0])) % 180
    return c, d, along, L, wid, ang, w8

segs = []
def visit(region, level):
    """Accept a region as one trail, or raise the threshold until it splits into trails."""
    lab, n = ndi.label(region, structure=np.ones((3, 3)))
    for i, sl in enumerate(ndi.find_objects(lab), 1):
        comp = lab[sl] == i
        ys, xs = np.nonzero(comp); ys = ys + sl[0].start; xs = xs + sl[1].start
        if len(xs) < 10: continue
        c, d, along, L, wid, ang, w8 = measure(ys, xs)
        if L >= 10 and L / wid >= 3 and wid <= 12 and 105 <= ang <= 145:
            a = c + d * along.min(); b = c + d * along.max()
            if a[1] < b[1]: a, b = b, a          # a = lower end
            n_s = max(int(L), 2)
            sx = np.clip(np.linspace(a[0], b[0], n_s).round().astype(int), 0, W - 1)
            sy = np.clip(np.linspace(a[1], b[1], n_s).round().astype(int), 0, H - 1)
            col = np.percentile(im[sy, sx], 80, axis=0)
            core = (w8 > 0.5 * w8.max()).sum() / max(L, 1)
            segs.append([round(a[0], 1), round(a[1], 1), round(b[0], 1), round(b[1], 1), [int(v) for v in col], round(float(w8.max()), 1), round(float(core), 2)])
        elif level < 6:
            sub = np.zeros_like(region); sub[sl] = comp
            visit(sub & (resp > thr * 2 ** (level + 1)), level + 1)
visit(mask & ~tree, 0)
print('segments', len(segs))

fill = ndi.binary_dilation(mask, iterations=2) & ~tree
w = (~(fill | tree)).astype(np.float32); plate = im.copy()
den = ndi.gaussian_filter(w, 5)
for k in range(3):
    num = ndi.gaussian_filter(np.where(w > 0, im[..., k], 0), 5)
    est = np.where(den > 0.15, num / np.maximum(den, 1e-3), ndi.median_filter(im[..., k], size=31))
    plate[..., k] = np.where(fill, np.minimum(est, im[..., k]), im[..., k])
Image.fromarray(np.clip(plate, 0, 255).astype(np.uint8)).save(out + '/plate.png')
Image.fromarray(np.dstack([im, tree_a * 255]).astype(np.uint8), 'RGBA').save(out + '/trees.png')
json.dump({'w': W, 'h': H, 'segs': segs}, open(out + '/trails.json', 'w'), separators=(',', ':'))
ov = Image.fromarray(im.astype(np.uint8)); dr = ImageDraw.Draw(ov)
for s in segs: dr.line(s[:4], fill=(255, 40, 40) if s[5] <= 60 else (40, 255, 40), width=1)
ov.save(out + '/overlay.png')
