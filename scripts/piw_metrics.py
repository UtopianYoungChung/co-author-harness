"""Read verified role traces and report observed timing; missing usage stays null."""
import argparse
import json
from pathlib import Path
import piw_coordinator as coordinator
import piw_native_host as native
import piw_session as piw


def measure(session):
    contract, _, log, state = coordinator.replay(session)
    roles = []
    for event in log['events']:
        if event['kind'] != 'role': continue
        request = piw.read_json(event['request']['path'])
        host = event['host']
        _, rows = native._rows(Path(host['child_log']), host['pins']['child']['bytes'])
        started = native.start_timestamp(contract['host'], rows, host)
        finished = host['finished_at']
        roles.append({'role': request['role'], 'phase': request['phase'], 'agent_execution_id': host['agent_execution_id'],
                      'started_at': started, 'finished_at': finished,
                      'elapsed_seconds': (native._time(finished) - native._time(started)).total_seconds(),
                      'request_to_finish_seconds': (native._time(finished) - native._time(request['created_at'])).total_seconds(),
                      'child_prefix_bytes': host['pins']['child']['bytes'], 'parent_prefix_bytes': host['pins']['parent']['bytes'],
                      'context_tokens': None, 'context_tokens_status': 'not available in the bound role receipt'})
    first = next((r for r in roles if r['role'] == 'generator'), None)
    elapsed = lambda stamp: (native._time(stamp) - native._time(contract['created_at'])).total_seconds()
    return {'schema_version': 'piw-metrics/v1', 'run_id': contract['run_id'], 'profile': contract['profile'],
            'host_adapter': contract['host']['adapter'], 'run_contract': piw.identity(Path(contract['session']['path']).parent / 'run.json'),
            'roles': roles, 'correction_cycles': state['corrections'], 'recorded_role_executions': len(roles),
            'failed_dispatches': None, 'failed_dispatches_status': 'unrecorded failures cannot be inferred from completed-role receipts',
            'time_to_first_candidate_seconds': elapsed(first['finished_at']) if first else None,
            'time_to_last_verified_role_seconds': elapsed(roles[-1]['finished_at']) if roles else None,
            'summed_role_seconds': sum(r['elapsed_seconds'] for r in roles),
            'stage': state['stage'], 'task_complete': False, 'quality_qualified': False, 'research_acceptance': False}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--piw-session', required=True, type=Path)
    args = parser.parse_args()
    try: result = measure(args.piw_session)
    except (piw.PIWError, OSError, ValueError, KeyError, TypeError) as exc:
        print(json.dumps({'ok': False, 'code': getattr(exc, 'code', 'PIW-METRICS-INVALID'), 'message': str(exc)}))
        return 2
    print(json.dumps(result, indent=2))
    return 0


if __name__ == '__main__': raise SystemExit(main())
