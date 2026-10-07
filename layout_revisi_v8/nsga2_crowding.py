"""
nsga2_crowding.py
Crowding distance (Deb et al., 2002) - mengukur kepadatan solusi lain di
sekitar sebuah individu dalam FRONT YANG SAMA. Tujuannya supaya solusi akhir
NSGA-II tersebar merata di sepanjang Pareto front, bukan menumpuk di satu
area saja.
"""

from nsga2_sorting import Individual


def calculate_crowding_distance(front: list[Individual]) -> None:
    """
    Mengisi field `crowding_distance` tiap individu dalam SATU front (in-place).

    Individu di 'ujung' front (nilai objective paling ekstrem, boundary
    solution) diberi jarak tak hingga supaya selalu diprioritaskan - ini
    menjaga keragaman di ujung-ujung Pareto front tetap terjaga.
    """
    jumlah = len(front)
    if jumlah == 0:
        return
    if jumlah <= 2:
        for ind in front:
            ind.crowding_distance = float("inf")
        return

    for ind in front:
        ind.crowding_distance = 0.0

    jumlah_objective = len(front[0].objectives)

    for m in range(jumlah_objective):
        front_terurut = sorted(front, key=lambda ind: ind.objectives[m])
        nilai_min = front_terurut[0].objectives[m]
        nilai_max = front_terurut[-1].objectives[m]

        front_terurut[0].crowding_distance = float("inf")
        front_terurut[-1].crowding_distance = float("inf")

        rentang = nilai_max - nilai_min
        if rentang == 0:
            continue  # semua individu sama di objective ini -> tidak menambah info

        for i in range(1, jumlah - 1):
            if front_terurut[i].crowding_distance == float("inf"):
                continue  # sudah jadi ujung di objective lain, biarkan tetap inf
            jarak_tetangga = (
                front_terurut[i + 1].objectives[m] - front_terurut[i - 1].objectives[m]
            ) / rentang
            front_terurut[i].crowding_distance += jarak_tetangga


def crowded_comparison(a: Individual, b: Individual) -> bool:
    """
    'Crowded-comparison operator' NSGA-II - True kalau A lebih baik dari B:
    - rank A lebih kecil (front lebih bagus/dominan), ATAU
    - rank sama, tapi crowding_distance A lebih besar (posisinya lebih
      'renggang', menjaga keragaman solusi)
    """
    if a.rank != b.rank:
        return a.rank < b.rank
    return a.crowding_distance > b.crowding_distance
