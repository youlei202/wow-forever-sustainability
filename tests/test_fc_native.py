from copy import deepcopy
import numpy as np
import pytest
from wowfs.experiments.fc_native import contexts,make_input,validate_equipment
from wowfs.experiments.fc_calibration import stat_input,damage_channels


def test_all_official_context_presets_are_legal():
    rows=contexts()
    assert len(rows)==56 and len({r['context_id'] for r in rows})==56
    assert sum(r['faction']=='Alliance' for r in rows)==28
    assert len({r['class'] for r in rows})==9
    for context in rows:
        value=make_input(context,{'duration':180},seed=1,iterations=1)
        validate_equipment(value)
    mage=next(c for c in rows if c['class']=='Mage')
    value=make_input(mage,{'duration':180},seed=1,iterations=1)
    value['request']['raid']['parties'][0]['players'][0]['equipment']['items'][14]={'id':18830}
    with pytest.raises(ValueError,match='weapon class'):
        validate_equipment(value)


def test_stat_override_preserves_equipment_entries():
    context=next(c for c in contexts() if c['class']=='Hunter')
    base=make_input(context,{'duration':180},seed=1,iterations=1)
    changed=stat_input(context,{'duration':180},125,125,seed=1,iterations=1)
    assert changed['request']==base['request']
    assert [list(v['stats']) for v in changed['research_variants']]==[['StatRangedAttackPower']]*2
    assert [v['stats']['StatRangedAttackPower'] for v in changed['research_variants']]==[125,125]


def test_damage_partition_excludes_self_damage_and_includes_pet():
    owner={'actions':[{'id':{'spellId':1},'spellSchool':2,
                      'targets':[{'unitIndex':0,'damage':10,'tickDamage':2},
                                 {'unitIndex':1,'damage':7,'tickDamage':0}]}],
           'pets':[{'actions':[{'id':{'spellId':2},'targets':[{'unitIndex':0,'damage':3,'tickDamage':0}]}]}]}
    output={'iterationsDone':1,'raidMetrics':{'parties':[{'players':[owner]}]},
            'encounterMetrics':{'targets':[{'unitIndex':0}]}}
    np.testing.assert_array_equal(damage_channels(output,1),[0,2,8,0,3])
