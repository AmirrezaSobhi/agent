"""Read-only TLS/API probe. Uses normal chain/hostname verification; sends no token."""
import argparse
import json
import socket
import ssl


def check(cafile=None):
    context=ssl.create_default_context(cafile=cafile)
    with socket.create_connection(('gitlab.local',443),timeout=5) as raw:
        with context.wrap_socket(raw,server_hostname='gitlab.local') as conn:
            cert=conn.getpeercert()
            conn.sendall(b'GET /api/v4/version HTTP/1.1\r\nHost: gitlab.local\r\nConnection: close\r\n\r\n')
            line=conn.makefile('rb').readline(256).decode('ascii',errors='replace')
            parts=line.split()
            if len(parts)<2 or parts[1] not in ('200','401'):
                raise ValueError('GitLab API did not return a valid unauthenticated response')
            return {'schema_version':1,'status':'PASS','hostname':'gitlab.local',
                    'tls':conn.version(),'chain_and_hostname_verified':True,
                    'api_status':int(parts[1]),'certificate_not_after':cert.get('notAfter'),
                    'token_sent':False}


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--approved-ca-file',help='Only a CA file specifically approved by the Product Owner')
    args=parser.parse_args()
    try:result=check(args.approved_ca_file)
    except (OSError,ValueError) as exc:
        print(json.dumps({'status':'BLOCKED','error_type':type(exc).__name__,'token_sent':False}))
        raise SystemExit(1)
    print(json.dumps(result))
