
from nox.sessions import InstallCache
def test_cache_empty(tmpdir):
    ic = InstallCache()
    ic.destroy(".")
    assert not ic.check(".", [1,2,3], 50)
    
    
from nox.sessions import InstallCache
def test_cache_good(tmpdir):
    ic = InstallCache()
    ic.add(".", [1,2,3])
    ic2 = InstallCache()
    assert ic2.check(".", [1,2,3], 50)
    
from nox.sessions import InstallCache
def test_cache_stale(tmpdir):
    ic = InstallCache()
    ic.add(".", [1,2,3])
    ic2 = InstallCache()
    assert not ic2.check(".", [1,2,3], -50)
