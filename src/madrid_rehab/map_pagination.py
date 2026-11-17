"""Bounded map pages, independent of the side list and its widget state."""

PAGE_SIZE = 500


def page_count(total):
    if total < 0:
        raise ValueError("Negative result count")
    return max(1, (total + PAGE_SIZE - 1) // PAGE_SIZE)


def page_refs(index, page):
    if page < 0 or page >= page_count(len(index)):
        raise ValueError("Map page out of bounds")
    return index.parcel_ref14.iloc[page * PAGE_SIZE : (page + 1) * PAGE_SIZE].tolist()
