"""
ga_operators.py (REVISI 2)
Operator genetika NSGA-II untuk kromosom terstruktur (lihat ga_encoding.py).
Semua operator hanya menghasilkan keputusan yang sah, jadi aturan susunan
tidak pernah rusak oleh crossover/mutasi.
"""

import random
from models import Layout
from ga_encoding import Chromosome, daftar_unit, gen_acak
from nsga2_sorting import Individual
from nsga2_crowding import crowded_comparison


def tournament_selection(population: list[Individual], ukuran_turnamen: int = 2) -> Individual:
    kandidat = random.sample(population, ukuran_turnamen)
    terbaik = kandidat[0]
    for ind in kandidat[1:]:
        if crowded_comparison(ind, terbaik):
            terbaik = ind
    return terbaik


def crossover(chrom1: Chromosome, chrom2: Chromosome, prob_crossover: float = 0.9):
    """Uniform crossover per UNIT keputusan (tiap bed / grup / bukaan diwariskan utuh)."""
    if random.random() > prob_crossover:
        return list(chrom1), list(chrom2)
    anak1: Chromosome = []
    anak2: Chromosome = []
    for g1, g2 in zip(chrom1, chrom2):
        if random.random() < 0.5:
            g1, g2 = g2, g1
        anak1.append(g1)
        anak2.append(g2)
    return anak1, anak2


def _lain(nilai: float, banyak: int) -> float:
    return float(random.choice([k for k in range(banyak) if k != int(nilai)]))


def mutate(chromosome: Chromosome, layout_template: Layout,
           prob_gen: float = 0.2, sigma_geser: float = 0.3) -> Chromosome:
    """
    Mutasi per unit (peluang prob_gen):
    - bed    : pindah pojok / putar / acak ulang
    - lemari : pindah dinding / ganti anchor / acak ulang
    - meja   : idem lemari (anchor 0..4)
    - pintu, jendela : geser posisi bebas (gaussian), ganti mode, atau acak ulang
    """
    unit = daftar_unit(layout_template)
    hasil: Chromosome = []
    for u, (a, b, c) in zip(unit, chromosome):
        tipe = u[0]
        if random.random() < prob_gen:
            r = random.random()
            if tipe == "bed":
                if r < 0.5:
                    a = _lain(a, 6)
                elif r < 0.8:
                    b = 90.0 if b == 0 else 0.0
                else:
                    a, b, c = gen_acak("bed")
            elif tipe in ("lemari", "meja"):
                banyak_anchor = 3 if tipe == "lemari" else 5
                if r < 0.4:
                    b = _lain(b, banyak_anchor)
                elif r < 0.75:
                    a = _lain(a, 4)
                else:
                    a, b, c = gen_acak(tipe)
            else:  # pintu / jendela
                banyak_mode = 4          # pintu: 0..3, jendela: 0..3 (REVISI 7: mode 3 = sejajar tengah bed)
                if r < 0.45:
                    b = min(max(b + random.gauss(0, 0.15), 0.0), 1.0)
                    a = 0.0
                elif r < 0.75:
                    a = _lain(a, banyak_mode)
                else:
                    a, b, c = gen_acak(tipe)
        hasil.append((a, b, c))
    return hasil
