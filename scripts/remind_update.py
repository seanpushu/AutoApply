"""A Windows-only notification: no network, model, job collection or app mutation."""
import argparse,ctypes,datetime,json,os
from pathlib import Path

def main():
 parser=argparse.ArgumentParser();parser.add_argument('--check',action='store_true');args=parser.parse_args()
 if os.name!='nt':raise RuntimeError('This reminder requires Windows.')
 user32=ctypes.WinDLL('user32',use_last_error=True)
 show=user32.MessageBoxTimeoutW
 show.argtypes=[ctypes.c_void_p,ctypes.c_wchar_p,ctypes.c_wchar_p,ctypes.c_uint,ctypes.c_ushort,ctypes.c_uint]
 show.restype=ctypes.c_int
 if args.check:
  print(json.dumps({'notificationAvailable':True,'networkCalls':0,'modelCalls':0,'automaticRefresh':False}));return
 result=show(None,'距上次提醒已到三天。是否现在更新 Summer 2027 实习岗位？\n\n需要更新时，在求职工作台点“确认更新”，或在 Codex 回复“更新岗位”。\n\n本通知没有采集岗位、调用模型或提交申请；不需要更新可直接关闭。','Summer 27 · 岗位更新提醒',0x40,0,25000)
 folder=Path(__file__).resolve().parents[1]/'data/reminder-history';folder.mkdir(parents=True,exist_ok=True)
 stamp=datetime.datetime.now(datetime.timezone.utc).strftime('%Y%m%dT%H%M%S%fZ')
 (folder/f'{stamp}.json').write_text(json.dumps({'at':stamp,'result':result,'modelCalls':0,'updatedJobs':False}),encoding='utf-8')
if __name__=='__main__':main()
