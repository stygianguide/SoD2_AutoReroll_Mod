import pstats
p = pstats.Stats("profile_output.txt")
p.sort_stats(pstats.SortKey.TIME).print_stats("so2_autoroll.py")