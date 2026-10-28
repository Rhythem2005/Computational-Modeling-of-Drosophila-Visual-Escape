"""Software-only fixtures; these states are not biological response evidence."""
from types import SimpleNamespace
import numpy as np
import pytest
from dashboard.simulation.room_flight.neural_output import AnatomicalOutput, MissingMotorMapping


def output():
    data=SimpleNamespace(body_ids=[11,22,33],get_dn_indices=lambda:[2])
    pipeline=SimpleNamespace(circuit=data,weights=np.array([[0.,0.,0.],[0.,0.,0.],[2.,3.,0.]]),simulation_config={'gain':.5})
    return AnatomicalOutput(SimpleNamespace(pipeline=pipeline,ids=np.array([11,22,33])))


def test_readout_and_input_decomposition_use_post_pre_and_actual_state():
    adapter=output();state=np.array([4.,6.,8.]);result=adapter.sample(state)
    np.testing.assert_array_equal(result['dn_body_ids'],[33])
    np.testing.assert_array_equal(result['dn_activity'],[8.])
    np.testing.assert_array_equal(result['dn_recurrent_input'],[13.])
    edges=adapter.incoming(33,state)
    np.testing.assert_array_equal(edges['pre_body_ids'],[11,22])
    np.testing.assert_array_equal(edges['modeled_contributions'],[4.,9.])
    state[0]=0
    assert adapter.sample(state)['dn_recurrent_input'][0]==9
    assert result['dn_activity'][0]==8  # owned snapshot
    assert not result['motor_mapping_available']
    with pytest.raises(MissingMotorMapping,match='No planner fallback'):
        adapter.motor_command()


@pytest.mark.parametrize('state',[[1,2],[1,float('nan'),3],[1,-1,3]])
def test_invalid_states_rejected(state):
    with pytest.raises(ValueError):output().sample(np.asarray(state))


def test_unknown_id_rejected():
    with pytest.raises(ValueError):output().incoming(999,np.zeros(3))


def test_room_recording_preserves_dn_clock_without_granting_motor_control(config,scene):
    from dashboard.simulation.room_flight.neural_adapter import NullDiagnostic
    from dashboard.simulation.room_flight.runner import RoomRunner
    class Diagnostic(NullDiagnostic):
        def sample(self,k):
            # Deliberately large fixture activity cannot initiate an escape.
            return dict(super().sample(k),dn_body_ids=np.array([33]),
                        dn_activity=np.array([100.]),dn_recurrent_input=np.array([50.]),
                        motor_mapping_available=False)
    result=RoomRunner(config(),'ordinary_motion',Diagnostic()).run(scene())
    arrays=result['arrays']
    assert arrays['dn_activity'].shape==(len(arrays['decision_times_ms']),1)
    assert not arrays['escape_event'].any()
    assert not arrays['motor_mapping_available'].any()
    baseline=RoomRunner(config(),'ordinary_motion').run(scene())
    assert result['commands']==baseline['commands']
    np.testing.assert_array_equal(arrays['fly_position'],baseline['arrays']['fly_position'])
