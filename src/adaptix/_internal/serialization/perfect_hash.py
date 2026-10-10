from collections.abc import Iterable
from dataclasses import dataclass

HASH_MASK = (1 << 32) - 1
HASH_PRIME = 16777619
HASH_SEED = 2166136261
MAX_HASH_ATTEMPTS = 32
MAX_DISPLACEMENT = 1024


def hash_bytes(data: bytes, seed: int) -> int:
    value = seed
    for byte in data:
        value = ((value ^ byte) * HASH_PRIME) & HASH_MASK
    return value


def arrange_hashes(hashes: tuple[int, ...], bucket_count: int):
    buckets = [[] for _ in range(bucket_count)]
    for index, value in enumerate(hashes):
        buckets[value & (bucket_count - 1)].append(index)
    slots = [None] * (bucket_count * 2)
    displacements = [0] * bucket_count
    for bucket in sorted(range(bucket_count), key=lambda index: -len(buckets[index])):
        indexes = buckets[bucket]
        if len(indexes) <= 1:
            continue
        for displacement in range(1, MAX_DISPLACEMENT):
            positions = [((hashes[index] * displacement & HASH_MASK) >> 16) & (len(slots) - 1) for index in indexes]
            if len(set(positions)) == len(positions) and all(slots[position] is None for position in positions):
                displacements[bucket] = displacement
                for position, index in zip(positions, indexes, strict=True):
                    slots[position] = index
                break
        else:
            return None
    free = iter(index for index, value in enumerate(slots) if value is None)
    for bucket, indexes in enumerate(buckets):
        if len(indexes) == 1:
            position = next(free)
            slots[position] = indexes[0]
            displacements[bucket] = -position - 1
    return tuple(displacements), tuple(slots)


@dataclass(frozen=True)
class PerfectHash:
    seed: int
    displacements: tuple[int, ...]
    entries: tuple[bytes | None, ...]
    names: tuple[str | None, ...]

    @classmethod
    def build(cls, names: Iterable[str]):
        names = tuple(dict.fromkeys(names))
        if not names:
            return None
        bucket_count = 1 << (len(names) - 1).bit_length()
        try:
            encoded = tuple(name.encode("utf-8") for name in names)
        except UnicodeEncodeError:
            return None
        for attempt in range(MAX_HASH_ATTEMPTS):
            seed = (HASH_SEED + attempt * HASH_PRIME) & HASH_MASK
            hashes = tuple(hash_bytes(name, seed) for name in encoded)
            if len(set(hashes)) != len(hashes):
                continue
            layout = arrange_hashes(hashes, bucket_count)
            if layout is not None:
                displacements, slots = layout
                return cls(
                    seed,
                    displacements,
                    tuple(encoded[index] if index is not None else None for index in slots),
                    tuple(names[index] if index is not None else None for index in slots),
                )
        # Hashing is an optimization. Adversarial names still work through
        # the ordinary string decoder when bounded table construction fails.
        return None

    def lookup(self, data: bytes) -> str | None:
        value = hash_bytes(data, self.seed)
        displacement = self.displacements[value & (len(self.displacements) - 1)]
        if displacement == 0:
            return None
        index = (
            -displacement - 1
            if displacement < 0
            else ((value * displacement & HASH_MASK) >> 16) & (len(self.entries) - 1)
        )
        return self.names[index] if self.entries[index] == data else None
