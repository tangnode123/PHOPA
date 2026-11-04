| N @ s=40^3 | proj SAT/MEMKILL | naive SAT/MEMKILL | proj med-solve | naive med-solve | proj med-ground | naive med-ground | ground ratio |
|---|---|---|---|---|---|---|---|
| N=60 | 4/1 | 5/0 | 23.0s | 30.4s | 7.7s | 27.5s | 3.6x |
| N=80 | 3/2 | 3/2 | 30.9s | 20.3s | 9.2s | 27.0s | 2.9x |
| N=100 | 1/4 | 0/5 | 59.0s | -- | 13.1s | -- | -- |

probe（1 rep/config，单 worker）：
- N60_s40_r0: proj 22.0s (ground 7.5s) | naive 112.2s (ground 27.6s)
- N100_s40_r0: proj 48.7s (ground 12.4s) | naive 48.1s (ground 36.5s)
- N60_s50_r0: proj MEMKILL (ground --) | naive MEMKILL (ground --)
- N100_s50_r0: proj MEMKILL (ground --) | naive MEMKILL (ground --)
