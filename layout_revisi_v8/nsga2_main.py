"""
nsga2_main.py
Main loop NSGA-II (Deb et al., 2002) - menggabungkan semua komponen dari
file-file sebelumnya jadi satu algoritma optimasi layout yang utuh.

Alur tiap generasi:
1. Bikin offspring (anak) sejumlah populasi, lewat tournament selection +
   crossover + mutasi dari populasi saat ini.
2. Evaluasi semua offspring (objective + constraint violation).
3. Gabungkan populasi lama + offspring (ukuran jadi 2x lipat).
4. Fast non-dominated sort gabungan tsb jadi beberapa front.
5. Bangun populasi generasi berikutnya: ambil front demi front sampai
   penuh; kalau front terakhir kelebihan, pilih yang crowding
   distance-nya paling besar (paling "renggang"/beragam).
"""

from models import Layout
from ga_encoding import init_population, decode, Chromosome
from nsga2_sorting import Individual, evaluate_individual, fast_non_dominated_sort
from nsga2_crowding import calculate_crowding_distance
from ga_operators import tournament_selection, crossover, mutate


def evaluate_population(population: list[Individual], layout_template: Layout) -> None:
    for ind in population:
        evaluate_individual(ind, layout_template)


def create_offspring(
    population: list[Individual],
    layout_template: Layout,
    ukuran_turnamen: int = 2,
    prob_crossover: float = 0.9,
    prob_gen_mutasi: float = 0.2,
    sigma_geser: float = 0.3,
) -> list[Individual]:
    """Bangun offspring sejumlah len(population), lewat seleksi+crossover+mutasi."""
    offspring: list[Individual] = []
    ukuran_populasi = len(population)

    while len(offspring) < ukuran_populasi:
        induk1 = tournament_selection(population, ukuran_turnamen)
        induk2 = tournament_selection(population, ukuran_turnamen)

        anak1, anak2 = crossover(induk1.chromosome, induk2.chromosome, prob_crossover)
        anak1 = mutate(anak1, layout_template, prob_gen_mutasi, sigma_geser)
        anak2 = mutate(anak2, layout_template, prob_gen_mutasi, sigma_geser)

        offspring.append(Individual(chromosome=anak1))
        if len(offspring) < ukuran_populasi:
            offspring.append(Individual(chromosome=anak2))

    return offspring


def select_next_generation(
    gabungan: list[Individual], ukuran_populasi: int
) -> list[Individual]:
    """
    Dari populasi gabungan (lama + offspring, ukuran 2N), pilih N individu
    terbaik untuk jadi populasi generasi berikutnya - front demi front,
    dengan crowding distance sebagai tie-breaker di front yang terpotong.
    """
    fronts = fast_non_dominated_sort(gabungan)
    generasi_berikutnya: list[Individual] = []

    for front in fronts:
        calculate_crowding_distance(front)
        if len(generasi_berikutnya) + len(front) <= ukuran_populasi:
            generasi_berikutnya.extend(front)
        else:
            sisa = ukuran_populasi - len(generasi_berikutnya)
            front_terurut = sorted(front, key=lambda ind: ind.crowding_distance, reverse=True)
            generasi_berikutnya.extend(front_terurut[:sisa])
            break

    return generasi_berikutnya


def run_nsga2(
    layout_template: Layout,
    ukuran_populasi: int = 60,
    jumlah_generasi: int = 100,
    ukuran_turnamen: int = 2,
    prob_crossover: float = 0.9,
    prob_gen_mutasi: float = 0.2,
    sigma_geser: float = 0.3,
    verbose: bool = False,
    kembalikan_populasi_penuh: bool = False,
):
    """
    Jalankan NSGA-II penuh, kembalikan Front 0 (Pareto-optimal) dari
    populasi akhir setelah `jumlah_generasi` iterasi.

    Kalau kembalikan_populasi_penuh=True, kembalikan tuple (front0, populasi)
    - populasi berisi SELURUH individu generasi terakhir (termasuk rank>0
      yang masih feasible). Berguna kalau butuh lebih banyak kandidat untuk
      keberagaman spasial (lihat pipeline.pilih_alternatif_beragam) - Front 0
      saja kadang terlalu sempit untuk menjamin alternatif yang tampak beda.
    """
    populasi = [Individual(chromosome=k) for k in init_population(layout_template, ukuran_populasi)]
    evaluate_population(populasi, layout_template)

    for generasi in range(jumlah_generasi):
        offspring = create_offspring(
            populasi, layout_template, ukuran_turnamen, prob_crossover, prob_gen_mutasi, sigma_geser
        )
        evaluate_population(offspring, layout_template)

        gabungan = populasi + offspring
        populasi = select_next_generation(gabungan, ukuran_populasi)

        if verbose and (generasi % 10 == 0 or generasi == jumlah_generasi - 1):
            jumlah_feasible = sum(1 for ind in populasi if ind.feasible)
            front0 = [ind for ind in populasi if ind.rank == 0]
            print(
                f"Gen {generasi:>4} | feasible: {jumlah_feasible:>3}/{ukuran_populasi} "
                f"| ukuran Front 0: {len(front0):>3}"
            )

    front0_akhir = [ind for ind in populasi if ind.rank == 0]
    if kembalikan_populasi_penuh:
        return front0_akhir, populasi
    return front0_akhir


def pareto_front_ke_layout(front: list[Individual], layout_template: Layout) -> list[Layout]:
    """Konversi Front 0 (list of Individual) balik jadi list Layout siap ditampilkan ke client."""
    return [decode(ind.chromosome, layout_template) for ind in front]
