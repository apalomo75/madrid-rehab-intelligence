"""Bounded pages over cadastral parcel identities."""

import numpy as np

PAGE_SIZE = 500


def page_count(total):
    if total < 0:
        raise ValueError("Negative result count")
    return max(1, (total + PAGE_SIZE - 1) // PAGE_SIZE)


def page_refs(index, page):
    if page < 0 or page >= page_count(len(index)):
        raise ValueError("Map page out of bounds")
    return index.parcel_ref14.iloc[page * PAGE_SIZE : (page + 1) * PAGE_SIZE].tolist()


def spatial_order(index):
    """Group adjacent cadastral centroids into pages along the longest axis."""

    if len(index) <= PAGE_SIZE:
        return index.reset_index(drop=True)
    coordinates = index[["x", "y"]].to_numpy()
    refs = np.argsort(index.parcel_ref14.to_numpy())
    ranks = np.empty_like(refs)
    ranks[refs] = np.arange(len(index))

    def partition(positions):
        pages = page_count(len(positions))
        if pages == 1:
            yield positions
            return
        points = coordinates[positions]
        axis = np.argmax(np.ptp(points, axis=0))
        order = np.lexsort((ranks[positions], points[:, axis]))
        ordered = positions[order]
        split = (pages // 2) * PAGE_SIZE
        yield from partition(ordered[:split])
        yield from partition(ordered[split:])

    positions = np.concatenate(list(partition(np.arange(len(index)))))
    return index.iloc[positions].reset_index(drop=True)
