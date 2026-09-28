"""Paired finite-domain simultaneous bounds for frozen native confirmation.

The two-sided Bonferroni t construction is APPROXIMATE, not distribution-free.
It covers a predeclared finite configuration/task contrast family when paired
seed vectors are independent across seed indices and t approximations are
adequate. Shared random streams within an index are retained, not ignored.
Configuration selection and every max/min below use the same simultaneous
family; no additional alpha is spent on enumerating histories in that domain.

The caller must freeze the domain, thresholds, reference configuration in each
task, alpha and analysis before confirmation. Samples must be complete physical
observations, not interpolation. This class cannot verify those provenance facts.
"""
from collections.abc import Mapping
import numpy as np
from scipy.stats import t as student_t


class FiniteBounds:
    """Finite response tensor inference with policies folded into configurations.

    samples: [configuration, task, paired seed].
    reference: [task, paired seed], repeating a development-frozen physical old
      reference in confirmation. Its uncertainty/covariance is part of every
      contrast; it is never treated as a fixed numeric sample mean.
    gain, tolerance, cap: fractions/multipliers of that reference, with contrasts
      U_a-U_b-gain*S, U_a-U_b+tolerance*S, and cap*S-U_a.

    All returned lower/upper feasibility booleans mean respectively "supported
    by the simultaneous intervals" / "not excluded by those intervals". An
    upper=True is only an optimistic relaxation, not a jointly feasible witness.
    """

    def __init__(self, samples, reference, gain, tolerance, cap, alpha):
        values=np.asarray(samples,dtype=float)
        refs=np.asarray(reference,dtype=float)
        if values.ndim!=3 or min(values.shape[:2],default=0)<1 or values.shape[2]<2:
            raise ValueError('samples must have shape [C>=1,Q>=1,N>=2]')
        if refs.shape!=values.shape[1:]:
            raise ValueError('reference must match task and paired seed axes')
        if not np.isfinite(values).all() or not np.isfinite(refs).all():
            raise ValueError('missing/nonfinite observations cannot be treated as zero')
        thresholds=np.asarray([gain,tolerance,cap,alpha],dtype=float)
        if not np.isfinite(thresholds).all() or gain<0 or tolerance<0 or cap<=0 or not 0<alpha<1:
            raise ValueError('require finite gain/tolerance>=0,cap>0,0<alpha<1')
        self.samples=values.copy(); self.samples.setflags(write=False)
        self.reference=refs.copy(); self.reference.setflags(write=False)
        self.count,self.tasks,self.n=self.samples.shape
        self.gain=float(gain); self.tolerance=float(tolerance)
        self.cap=float(cap); self.alpha=float(alpha)
        self.means=self.samples.mean(axis=2); self.ref=self.reference.mean(axis=1)
        if np.any(self.ref<=0):
            raise ValueError('each physical reference must have positive mean performance')
        self.family_size=self.tasks*(2*self.count*self.count+self.count)
        # isf avoids loss of precision from subtracting a very small tail from 1.
        self.critical=float(student_t.isf(self.alpha/(2*self.family_size),self.n-1))
        if not np.isfinite(self.critical):
            raise ValueError('critical value is not finite')
        self.pairs={};self.pair_means={}
        for offset in dict.fromkeys((self.gain,-self.tolerance)):
            mean=np.empty((self.tasks,self.count,self.count))
            lower=np.empty_like(mean);upper=np.empty_like(mean)
            # Compute paired vectors directly. This includes all covariance terms
            # and preserves exact zero variance without cancellation of two large
            # marginal variance estimates. Memory is O(C*N), not O(C*C*N).
            for q in range(self.tasks):
                for i in range(self.count):
                    contrast=self.samples[i,q][None,:]-self.samples[:,q,:]-offset*self.reference[q][None,:]
                    m,lo,hi=self._paired_interval(contrast)
                    mean[q,i]=m;lower[q,i]=lo;upper[q,i]=hi
            self.pairs[offset]=(lower,upper);self.pair_means[offset]=mean
        self.cap_mean,self.cap_lower,self.cap_upper=self._paired_interval(
            self.cap*self.reference[None,:,:]-self.samples)
        # Compatibility names match the existing older paired-bound class, but
        # these cap margins have POSITIVE feasible direction (the old class did not).
        self.cap_low=self.cap_lower;self.cap_high=self.cap_upper

    def _paired_interval(self, contrast):
        mean=contrast.mean(axis=-1)
        se=contrast.std(axis=-1,ddof=1)/np.sqrt(self.n)
        radius=self.critical*se
        return mean,mean-radius,mean+radius

    def _indices(self, indices, *, empty=False):
        raw=list(indices)
        if any(isinstance(i,(bool,np.bool_)) or not isinstance(i,(int,np.integer)) for i in raw):
            raise ValueError('configuration indices must be integers')
        if any(i<0 or i>=self.count for i in raw):
            raise ValueError('configuration index outside frozen finite domain')
        result=np.asarray(sorted(set(int(i) for i in raw)),dtype=int)
        if not empty and not len(result):
            raise ValueError('frontier requires a nonempty configuration set')
        return result

    def _weights(self, weights):
        result=np.full(self.tasks,1/self.tasks) if weights is None else np.asarray(weights,dtype=float)
        if result.shape!=(self.tasks,) or not np.isfinite(result).all() or np.any(result<0):
            raise ValueError('task weights must be finite, nonnegative, and task-shaped')
        if not np.isclose(result.sum(),1.,rtol=0.,atol=1e-12):
            raise ValueError('task weights must sum to one; no silent renormalization')
        return result

    @staticmethod
    def _mass_requirement(value,name):
        if not np.isfinite(value) or not 0<float(value)<=1:
            raise ValueError(name+' must be in (0,1]')
        return float(value)

    def frontier_contrast(self,left,right,offset):
        """Bound max(left)-max(right)-offset*reference separately for each task.

        lower = max_left min_right pair_lower;
        upper = min_right max_left pair_upper.
        Only the two offsets registered in __init__ may be queried. A new offset
        needs a new predeclared family, not reuse of the old error budget.
        """
        left=self._indices(left);right=self._indices(right)
        offset=float(offset)
        if offset not in self.pairs:
            raise ValueError('offset was not included in the simultaneous family')
        lo,hi=self.pairs[offset]
        lo=lo[:,left][:,:,right];hi=hi[:,left][:,:,right]
        return lo.min(axis=2).max(axis=1),hi.max(axis=1).min(axis=1)

    def _frontier_summary(self,left,right,offset):
        left=self._indices(left);right=self._indices(right)
        low,high=self.frontier_contrast(left,right,offset)
        mean=self.means[left].max(axis=0)-self.means[right].max(axis=0)-offset*self.ref
        return {'mean':mean,'lower':low,'upper':high}

    @staticmethod
    def _status(lower,upper):
        return 'interval_supported' if lower else ('interval_excluded' if not upper else 'unresolved')

    @staticmethod
    def _serial_margins(margins):
        return {key:np.asarray(value,dtype=float).tolist() for key,value in margins.items()}

    def _mass_check(self,margins,weights,required):
        masses={key:float(weights[np.asarray(value)>=0.].sum()) for key,value in margins.items()}
        passed={key:bool(value>=required-1e-12) for key,value in masses.items()}
        return {**passed,'mass':masses,'required_mass':required,
                'task_margins':self._serial_margins(margins),
                'task_pass':{key:(np.asarray(value)>=0.).tolist() for key,value in margins.items()},
                'statistical_status':self._status(passed['lower'],passed['upper'])}

    def evaluate(self,stateconfig_indices,source_indices,weights,retention_mass):
        """Assess full-state power and every supplied old/new source's usefulness.

        source_indices maps each released source ID to ALL global configurations
        containing it. Intersecting those incidences with the state supports
        fixed partners, both-updated slots, and finite policy libraries equally.
        The caller must supply every released old AND new source and the complete
        legal state domain. The method never deletes an overpowered combination.
        """
        state=self._indices(stateconfig_indices)
        weights=self._weights(weights)
        required=self._mass_requirement(retention_mass,'retention_mass')
        if not isinstance(source_indices,Mapping) or not len(source_indices):
            raise ValueError('source_indices must map every released source to its incidence set')
        margins={'mean':self.cap_mean[state].min(axis=0),
                 'lower':self.cap_lower[state].min(axis=0),
                 'upper':self.cap_upper[state].min(axis=0)}
        power={key:bool(np.all(value>=0.)) for key,value in margins.items()}
        power.update(task_margins=self._serial_margins(margins),
                     configuration_indices=state.tolist(),
                     individual_margins=self._serial_margins({
                         'mean':self.cap_mean[state],'lower':self.cap_lower[state],
                         'upper':self.cap_upper[state]}))
        power['statistical_status']=self._status(power['lower'],power['upper'])
        sources={}
        for source,incidence in source_indices.items():
            if not isinstance(source,str):
                raise ValueError('source IDs must be strings for unambiguous serialized results')
            available=np.intersect1d(state,self._indices(incidence,empty=True))
            if len(available):
                source_margins=self._frontier_summary(available,state,-self.tolerance)
                check=self._mass_check(source_margins,weights,required)
            else:
                # An absent source has no witness on any task; it is excluded,
                # not merely unknown. Avoid nonstandard JSON +/-Infinity values.
                check={'mean':False,'lower':False,'upper':False,
                       'mass':{'mean':0.,'lower':0.,'upper':0.},'required_mass':required,
                       'task_margins':{key:[None]*self.tasks for key in ('mean','lower','upper')},
                       'task_pass':{key:[False]*self.tasks for key in ('mean','lower','upper')},
                       'statistical_status':'interval_excluded','reason':'source_absent_from_state'}
            check['configuration_indices']=available.tolist()
            sources[source]=check
        retention={key:all(s[key] for s in sources.values()) for key in ('mean','lower','upper')}
        retention['statistical_status']=self._status(retention['lower'],retention['upper'])
        outcome={key:bool(power[key] and retention[key]) for key in ('mean','lower','upper')}
        return {**outcome,'statistical_status':self._status(outcome['lower'],outcome['upper']),
                'checks':{'power':power,'retention':retention},'sources':sources,
                'stateconfig_indices':state.tolist(),'frontier_mean':self.means[state].max(axis=0).tolist(),
                'reference_mean':self.ref.tolist(),'weights':weights.tolist(),
                'scope':'approximate simultaneous t; complete declared finite physical domain only',
                'upper_interpretation':'optimistic necessary conditions, not a joint feasible witness'}

    def transition(self,prev,current,source_indices,gain_mass,*,weights=None,retention_mass=1.):
        """Assess a release edge, including history, full power and all sources.

        Pass frozen weights and retention_mass explicitly in scientific analyses.
        Defaults are equal task weights and retention on all tasks. Source IDs
        include every old/new released source at the CURRENT state. prev must be
        a subset of current; removal of an old physical configuration is not a
        release under this interface.
        """
        before=self._indices(prev);after=self._indices(current)
        weights=self._weights(weights)
        required=self._mass_requirement(gain_mass,'gain_mass')
        state=self.evaluate(after,source_indices,weights,retention_mass)
        gain=self._mass_check(self._frontier_summary(after,before,self.gain),weights,required)
        retained=bool(np.isin(before,after).all())
        history={key:retained for key in ('mean','lower','upper')}
        history['removed_configuration_indices']=np.setdiff1d(before,after).tolist()
        outcome={key:bool(state[key] and gain[key] and retained) for key in ('mean','lower','upper')}
        return {**outcome,'statistical_status':self._status(outcome['lower'],outcome['upper']),
                'checks':{**state['checks'],'gain':gain,'history':history},
                'sources':state['sources'],'previous_stateconfig_indices':before.tolist(),
                'stateconfig_indices':after.tolist(),
                'previous_frontier_mean':self.means[before].max(axis=0).tolist(),
                'frontier_mean':state['frontier_mean'],'reference_mean':self.ref.tolist(),
                'weights':weights.tolist(),'scope':state['scope'],
                'upper_interpretation':state['upper_interpretation']}

    def manifest(self):
        return {'configurations':self.count,'tasks':self.tasks,'paired_seeds':self.n,
                'gain':self.gain,'tolerance':self.tolerance,'cap':self.cap,'alpha':self.alpha,
                'family_size':self.family_size,'degrees_of_freedom':self.n-1,
                'critical_value':self.critical,
                'contrast_family':'Q*(2*C*C+C), two-sided Bonferroni paired t',
                'guarantee':'Approximate t, not exact or distribution-free; fixed-sample, frozen finite domain.',
                'paired_dependence':'Preserved within seed, independence assumed across seed indices.',
                'zero_standard_error':'Point intervals; no artificial variance floor.',
                'capacity_upper_bound_rule':'Retain every state/edge with upper=True; an optimistic relaxation only.'}
