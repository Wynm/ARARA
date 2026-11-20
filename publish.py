"""Explicit, one-shot platform uploads. A pending receipt blocks ambiguous retries."""
import argparse
import json
import os
from pathlib import Path


def youtube_auth(interactive=False):
    from google.oauth2.credentials import Credentials
    from google.auth.transport.requests import Request
    from google_auth_oauthlib.flow import InstalledAppFlow
    scope=['https://www.googleapis.com/auth/youtube.upload']
    token=Path('secrets/youtube.token.json')
    if interactive:
        flow=InstalledAppFlow.from_client_secrets_file('secrets/client_secret.json',scope)
        creds=flow.run_local_server(port=0,access_type='offline',prompt='consent')
        token.write_text(creds.to_json(),encoding='utf8')
    else:
        # Colab supplies its secret to this process only; never copy it to Drive.
        payload = os.environ.get('YOUTUBE_TOKEN_JSON')
        if payload:
            creds = Credentials.from_authorized_user_info(json.loads(payload), scope)
        else:
            creds = Credentials.from_authorized_user_file(str(token), scope)
        if not creds.valid:
            creds.refresh(Request())
    return creds


def publish(job,target):
    job=Path(job); video=job/'lesson.mp4'
    m=json.loads((job/'metadata.json').read_text(encoding='utf8'))
    if not video.is_file():
        raise FileNotFoundError(video)
    receipt=job/(target+'.json')
    if receipt.exists():
        if json.loads(receipt.read_text(encoding='utf8')).get('state') != 'uploaded':
            raise RuntimeError(f'Check the platform before retrying: {receipt}')
        print(f'{target}: see existing receipt {receipt}; no upload.'); return
    if target=='youtube':
        from googleapiclient.discovery import build
        from googleapiclient.http import MediaFileUpload
        visibility=os.getenv('YOUTUBE_VISIBILITY','private')
        if visibility not in ('public','unlisted','private'):
            raise ValueError('Invalid YOUTUBE_VISIBILITY')
        api=build('youtube','v3',credentials=youtube_auth())
        request=api.videos().insert(part='snippet,status',body={
            'snippet':{'title':m['title'],'description':m['description'],'tags':m['tags'],'categoryId':'27','defaultLanguage':'ar'},
            'status':{'privacyStatus':visibility}}, media_body=MediaFileUpload(str(video),mimetype='video/mp4',resumable=True))
    elif target=='facebook':
        import requests
        page=os.environ['FB_PAGE_ID']; token=os.environ['FB_PAGE_TOKEN']
        if not page.isdecimal():
            raise ValueError('Invalid FB_PAGE_ID')
    else:
        raise ValueError('Unknown target')
    with receipt.open('x') as f:
        json.dump({'state':'pending'},f)
    if target=='youtube':
        result=request.execute()
    else:
        with video.open('rb') as f:
            response=requests.post(f'https://graph-video.facebook.com/v24.0/{page}/videos',headers={'Authorization':'Bearer '+token},data={'title':m['title'],'description':m['description']},files={'source':('lesson.mp4',f,'video/mp4')},timeout=(15,300))
        response.raise_for_status(); result=response.json()
    receipt.write_text(json.dumps({'state':'uploaded','id':result['id']}),encoding='utf8')
    print(f'{target}: {receipt}')


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    sub=parser.add_subparsers(dest='cmd',required=True); sub.add_parser('authorize-youtube')
    upload=sub.add_parser('upload'); upload.add_argument('job'); upload.add_argument('target',choices=['youtube','facebook'])
    args=parser.parse_args()
    if args.cmd=='authorize-youtube': youtube_auth(True)
    else: publish(args.job,args.target)
