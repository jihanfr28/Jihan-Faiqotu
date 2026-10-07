"""
nsga2_sorting.py
Bagian inti NSGA-II: struktur Individual, constrained-domination,
dan fast non-dominated sorting (Deb, Pratap, Agarwal, Meyarivan - 2002).
"""

from dataclasses import dataclass, field
from models import Layout
from constraints import check_all_constraints, JENIS_HARD
from objectives import evaluate_dengan_jangkauan, pelanggaran_jangkauan
from ga_encoding import Chromosome, decode


@dataclass
class Individual:
    """Satu individu dalam populasi NSGA-II: kromosom + hasil evaluasinya."""
    chromosome: Chromosome
    objectives: tuple = field(default=None)
    constraint_violation: float = 0.0   # total besaran pelanggaran hard constraint (0 = feasible)
    rank: int = -1                      # indeks Pareto front, 0 = front terbaik
    crowding_distance: float = 0.0

    @property
    def feasible(self) -> bool:
        return self.constraint_violation <= 0.0


def evaluate_individual(individual: Individual, layout_template: Layout) -> None:
    """
    Isi field `objectives` & `constraint_violation` individu berdasarkan
    layout_template (room/furniture/crew tetap) + kromosom individu ini.
    Mengubah individual secara in-place.
    """
    layout = decode(individual.chromosome, layout_template)
    semua = check_all_constraints(layout)
    individual.objectives, n_tak = evaluate_dengan_jangkauan(layout, semua)
    semua = semua + pelanggaran_jangkauan(layout, n_tak)

    # WAJIB (hard): struktur fisik, pintu bisa dibuka, lemari bisa dibuka, ABK bisa menjangkau
    # semua furniture. Jarak/akses lain (kursi, bed) soft -> masuk objective ergonomi.
    pelanggaran = [v for v in semua if v.hard or v.jenis in JENIS_HARD]
    total = sum(v.besaran for v in pelanggaran)
    # beberapa jenis pelanggaran (mis. keluar_ruangan, blokir_bukaan) kadang
    # besaran-nya 0/kecil - pastikan tetap terhitung infeasible kalau ADA pelanggaran
    if pelanggaran and total <= 0.0:
        total = len(pelanggaran) * 0.01
    individual.constraint_violation = total


def dominates(a: Individual, b: Individual) -> bool:
    """
    Constrained-domination (Deb, 2002) - aturan "A mengalahkan B":
    1) A feasible, B tidak feasible          -> A menang
    2) A tidak feasible, B feasible          -> A kalah
    3) Keduanya tidak feasible               -> pelanggaran lebih kecil yang menang
    4) Keduanya feasible                     -> Pareto dominance biasa:
       A menang kalau semua objective A <= B, DAN minimal 1 objective A < B
       (semua objective di sini MINIMIZE, sesuai konvensi objectives.py)
    """
    if a.feasible and not b.feasible:
        return True
    if (not a.feasible) and b.feasible:
        return False
    if (not a.feasible) and (not b.feasible):
        return a.constraint_violation < b.constraint_violation

    tidak_lebih_buruk = all(x <= y for x, y in zip(a.objectives, b.objectives))
    ada_lebih_baik = any(x < y for x, y in zip(a.objectives, b.objectives))
    return tidak_lebih_buruk and ada_lebih_baik


def fast_non_dominated_sort(population: list[Individual]) -> list[list[Individual]]:
    """
    Kelompokkan populasi jadi Pareto front berlapis (front[0] = terbaik).
    Juga mengisi `individual.rank` untuk tiap individu (0 = front terbaik).
    Kompleksitas O(N^2 * M) - standar algoritma NSGA-II asli.
    """
    fronts: list[list[Individual]] = [[]]
    domination_count = {id(ind): 0 for ind in population}
    dominated_set = {id(ind): [] for ind in population}

    for p in population:
        for q in population:
            if p is q:
                continue
            if dominates(p, q):
                dominated_set[id(p)].append(q)
            elif dominates(q, p):
                domination_count[id(p)] += 1
        if domination_count[id(p)] == 0:
            p.rank = 0
            fronts[0].append(p)

    i = 0
    while fronts[i]:
        next_front = []
        for p in fronts[i]:
            for q in dominated_set[id(p)]:
                domination_count[id(q)] -= 1
                if domination_count[id(q)] == 0:
                    q.rank = i + 1
                    next_front.append(q)
        i += 1
        fronts.append(next_front)

    fronts.pop()  # front terakhir yang kosong (kondisi berhenti while)
    return fronts
