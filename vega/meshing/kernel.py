"""Serialize Gmsh's process-global model and disable signal handlers in workers."""
from contextlib import contextmanager
from threading import RLock
import gmsh

_LOCK = RLock()


@contextmanager
def model(name):
    with _LOCK:
        gmsh.initialize(['vega', '-nopopup'], readConfigFiles=False, interruptible=False)
        try:
            gmsh.option.setNumber('General.Terminal', 0)
            gmsh.option.setNumber('General.NumThreads', 1)
            gmsh.option.setNumber('Mesh.RandomSeed', 1)
            gmsh.model.add(name)
            yield gmsh
        finally:
            gmsh.finalize()
