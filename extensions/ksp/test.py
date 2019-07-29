import ksp
import os
p = os.path.join(os.getcwd(),'src','ksp','sample','sample.gr')
res = ksp.k_shortest_paths(p,3,0.8,0,4,'mp')
print(res)
