import numpy as np
from wowfs.experiments.fc_results import PairedBounds,cover,task_masks


def test_frontier_gain_checks_every_old_competitor():
    reference=np.full((1,32),100.)
    uncertain_old=reference.copy();uncertain_old[0,:16]-=40;uncertain_old[0,16:]+=40
    samples=np.stack([reference,uncertain_old,reference+2])
    bounds=PairedBounds(samples,reference)
    lo,hi=bounds.frontier_contrast([2],[0,1],.01)
    assert samples[2].mean()-max(samples[0].mean(),samples[1].mean())==2
    assert lo[0]<0<hi[0]
    # Omitting the uncertain old competitor would incorrectly certify this
    # sample as the same problem as a known fixed old frontier.
    assert bounds.frontier_contrast([2],[0],.01)[0][0]>0


def test_exact_cover_requires_all_eight_equal_weight_tasks():
    weights=np.full(8,.125)
    near=np.array([[1]*7+[0],[0]*7+[1]],dtype=bool)
    assert len(cover(task_masks(near),weights))==2
    assert cover(task_masks(near[:1]),weights) is None


def test_reference_pairing_cancels_proportional_gain_noise():
    reference=np.arange(1.,33.)[None,:]
    samples=np.stack([reference,1.01*reference])
    bounds=PairedBounds(samples,reference)
    lo,hi=bounds.frontier_contrast([1],[0],.01)
    assert abs(lo[0])<1e-8 and abs(hi[0])<1e-8
