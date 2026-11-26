"""N-body simulation — the classic 5-planet solar-system benchmark.

Simulates the Sun and four Jovian planets for a number of timesteps using the
symmetric symplectic integrator from the benchmarks game, then reports the
total energy per unit mass. Eight parallel arrays keep the inner loop free of
struct access, and the whole thing is about 50 lines.
"""
import math

PI = 3.141592653589793
SOLAR_MASS = 4 * PI * PI
DAYS_PER_YEAR = 365.24

NAMES = ["sun", "jupiter", "saturn", "uranus", "neptune"]

# mass, x, y, z, vx, vy, vz — AU and AU/day
BODIES = [
    (SOLAR_MASS, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0),
    (9.54791938424326609e-04, 4.84143144246472090e+00, -1.16032004402742839e+00,
     -1.03622044471123109e-01, 1.66007664274403694e-03 * DAYS_PER_YEAR,
     7.69901118419740425e-03 * DAYS_PER_YEAR, -6.90460016972063023e-05 * DAYS_PER_YEAR),
    (2.85885980666130812e-04, 8.34336671824457987e+00, 4.12479856412430479e+00,
     -4.03523417114321381e-01, -2.76742510726862411e-03 * DAYS_PER_YEAR,
     4.99852801234917238e-03 * DAYS_PER_YEAR, 2.30417297573763929e-05 * DAYS_PER_YEAR),
    (4.36624404335156298e-05, 1.28943695621391310e+01, -1.51111514016986312e+01,
     -2.23307578892655734e-01, 2.96460137564761618e-03 * DAYS_PER_YEAR,
     2.37847173959480950e-03 * DAYS_PER_YEAR, -2.96589568540237556e-05 * DAYS_PER_YEAR),
    (5.15138902046611451e-05, 1.53796971148509165e+01, -2.59193146099879641e+01,
     1.79258772950371181e-01, 2.68067772490389322e-03 * DAYS_PER_YEAR,
     1.62824170038242295e-03 * DAYS_PER_YEAR, -9.51592254519715870e-05 * DAYS_PER_YEAR),
]


def advance(dt, n, mass, x, y, z, vx, vy, vz):
    for _ in range(n):
        for i in range(len(mass) - 1):
            for j in range(i + 1, len(mass)):
                dx = x[i] - x[j]
                dy = y[i] - y[j]
                dz = z[i] - z[j]
                d2 = dx * dx + dy * dy + dz * dz
                mag = dt / (d2 * math.sqrt(d2))
                mi, mj = mass[i], mass[j]
                vx[i] -= dx * mj * mag
                vy[i] -= dy * mj * mag
                vz[i] -= dz * mj * mag
                vx[j] += dx * mi * mag
                vy[j] += dy * mi * mag
                vz[j] += dz * mi * mag
        for i in range(len(mass)):
            x[i] += dt * vx[i]
            y[i] += dt * vy[i]
            z[i] += dt * vz[i]


def energy(mass, x, y, z, vx, vy, vz):
    e = 0.0
    for i in range(len(mass)):
        e += 0.5 * mass[i] * (vx[i] ** 2 + vy[i] ** 2 + vz[i] ** 2)
        for j in range(i + 1, len(mass)):
            dx = x[i] - x[j]
            dy = y[i] - y[j]
            dz = z[i] - z[j]
            e -= (mass[i] * mass[j]) / math.sqrt(dx * dx + dy * dy + dz * dz)
    return e


def offset_momentum(mass, x, y, z, vx, vy, vz):
    px = py = pz = 0.0
    for i in range(len(mass)):
        px += vx[i] * mass[i]
        py += vy[i] * mass[i]
        pz += vz[i] * mass[i]
    vx[0] = -px / SOLAR_MASS
    vy[0] = -py / SOLAR_MASS
    vz[0] = -pz / SOLAR_MASS


def run(steps):
    mass = [b[0] for b in BODIES]
    x = [b[1] for b in BODIES]
    y = [b[2] for b in BODIES]
    z = [b[3] for b in BODIES]
    vx = [b[4] for b in BODIES]
    vy = [b[5] for b in BODIES]
    vz = [b[6] for b in BODIES]
    offset_momentum(mass, x, y, z, vx, vy, vz)
    print("%.9f" % energy(mass, x, y, z, vx, vy, vz))
    advance(0.01, steps, mass, x, y, z, vx, vy, vz)
    print("%.9f" % energy(mass, x, y, z, vx, vy, vz))


if __name__ == "__main__":
    run(500000)
