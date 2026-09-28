"""Common, data-independent library warmup for the isolated benchmark server."""
from pathlib import Path
import sys
from ortools.sat.python import cp_model
from pysat.solvers import Glucose4
from pysat.pb import PBEnc
from .co_exact import Model
from .co_generic import CPSatSolver,IncrementalSAT
from .co_reference import solve
from . import co_benchmark
Path(__file__).with_name("co_benchmark_ipc.py").read_bytes()

model=Model.from_dict({'slots':{'a':0,'b':0,'x':1},
 'configurations':[{'support':['a','x'],'values':['1']},{'support':['b','x'],'values':['2']}],
 'history':['a','x'],'weights':['1'],'tolerance':['2'],'cap':['3'],'gain':['1'],
 'required_mass':'1','gain_mass':'1'})
for method in (CPSatSolver,IncrementalSAT):
 s=method(model)
 try:assert s.query(['b'])['status']=='YES'
 finally:s.close()
assert solve(model,['b'])['status']=='YES'
# Force shared object file pages into the ordinary OS page cache once. This
# avoids attributing remote filesystem cold-page stalls to one solver method.
for module in tuple(sys.modules.values()):
 p=getattr(module,'__file__',None)
 if p and str(p).endswith('.so'):
  with open(p,'rb') as stream:
   while stream.read(1024*1024):pass
