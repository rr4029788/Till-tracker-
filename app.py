from flask import Flask, request, jsonify, render_template_string, session, redirect
import json, os, hashlib
from datetime import datetime

app = Flask(__name__)
app.secret_key = 'change-this-to-any-random-word-12345'
SHOPS_FILE = 'shops.json'
TX_FILE = 'transactions.json'

def load_shops():
    if os.path.exists(SHOPS_FILE):
        with open(SHOPS_FILE) as f: return json.load(f)
    return {}

def save_shops(s):
    with open(SHOPS_FILE,'w') as f: json.dump(s,f)

def load_tx():
    if os.path.exists(TX_FILE):
        with open(TX_FILE) as f: return json.load(f)
    return []

def save_tx(d):
    with open(TX_FILE,'w') as f: json.dump(d,f)

def hash_pw(p): return hashlib.sha256(p.encode()).hexdigest()

# ---------- PAGES ----------
LOGIN_HTML = '''
<html><head><meta name="viewport" content="width=device-width, initial-scale=1">
<style>body{font-family:sans-serif;padding:20px;background:#f2f2f2} .box{background:white;padding:20px;border-radius:12px;max-width:400px;margin:auto}
input{width:100%;padding:14px;margin:8px 0;border-radius:8px;border:1px solid #ccc;font-size:16px;box-sizing:border-box}
button{width:100%;padding:14px;background:#0a8a00;color:white;border:none;border-radius:8px;font-size:18px;margin-top:10px}
a{display:block;text-align:center;margin-top:15px;color:#0a8a00}</style></head><body>
<div class="box"><h2>🏪 Till Tracker - Multi Shop</h2>
<input id="till" placeholder="Till Number e.g 7893542">
<input id="pw" type="password" placeholder="Password">
<button onclick="login()">LOGIN</button>
<p id="msg" style="color:red"></p>
<a href="/signup">No account? Create Shop Account</a></div>
<script>async function login(){
 let till=document.getElementById('till').value; let pw=document.getElementById('pw').value;
 let r=await fetch('/api/login',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({till,pw})});
 let j=await r.json(); if(j.ok) location.href='/dashboard'; else document.getElementById('msg').innerText=j.error;
}</script></body></html>
'''

SIGNUP_HTML = '''
<html><head><meta name="viewport" content="width=device-width, initial-scale=1">
<style>body{font-family:sans-serif;padding:20px;background:#f2f2f2} .box{background:white;padding:20px;border-radius:12px;max-width:450px;margin:auto}
input{width:100%;padding:14px;margin:8px 0;border-radius:8px;border:1px solid #ccc;font-size:16px;box-sizing:border-box}
button{width:100%;padding:14px;background:#0a8a00;color:white;border:none;border-radius:8px;font-size:18px;margin-top:10px}
.code{background:#f0f0f0;padding:12px;border-radius:8px;word-break:break-all;font-size:13px;margin:10px 0}</style></head><body>
<div class="box"><h2>Create Shop Account</h2>
<input id="shop_name" placeholder="Shop Name e.g Mama Mboga">
<input id="owner" placeholder="Owner Name e.g John Kamau">
<input id="till" placeholder="Till Number e.g 7893542">
<input id="pw" type="password" placeholder="Create Password">
<button onclick="signup()">CREATE ACCOUNT</button>
<p id="msg"></p>
<div id="result" style="display:none">
<h3>✅ Account Created!</h3>
<p>Now copy these 2 URLs to Daraja (or give to me to register for you):</p>
<b>Confirmation URL:</b><div class="code" id="conf"></div>
<b>Validation URL:</b><div class="code" id="val"></div>
<a href="/">Go to Login</a></div></div>
<script>async function signup(){
 let shop_name=document.getElementById('shop_name').value; let owner=document.getElementById('owner').value; let till=document.getElementById('till').value; let pw=document.getElementById('pw').value;
 let r=await fetch('/api/signup',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({shop_name,owner,till,pw})});
 let j=await r.json(); if(j.ok){ document.getElementById('result').style.display='block'; document.getElementById('conf').innerText=j.confirmation_url; document.getElementById('val').innerText=j.validation_url; document.getElementById('msg').innerText=''; } else document.getElementById('msg').innerText=j.error;
}</script></body></html>
'''

DASHBOARD_HTML = '''
<html><head><meta name="viewport" content="width=device-width, initial-scale=1">
<style>body{font-family:sans-serif;padding:12px;background:#f2f2f2}
input{width:100%;padding:14px;font-size:18px;margin:5px 0;border-radius:8px;border:1px solid #ccc;box-sizing:border-box}
button{width:100%;padding:14px;background:#0a8a00;color:white;border:none;font-size:18px;border-radius:8px}
table{width:100%;background:white;border-collapse:collapse;margin-top:10px}
th,td{padding:10px;text-align:left;border-bottom:1px solid #ddd;font-size:15px}
.received{color:green;font-weight:bold}.sent{color:red;font-weight:bold}
.tick-btn{font-size:28px;width:55px;height:55px;border:2px solid #999;border-radius:10px;background:white}
.tick-btn.done{background:#d4edda;border-color:green}.confirmed-row{background:#e8f5e9}
.top{display:flex;justify-content:space-between;align-items:center}.logout{background:#d32f2f;padding:8px 15px;width:auto;font-size:14px}</style></head><body>
<div class="top"><h2 id="shop_title">Loading...</h2><button class="logout" onclick="location.href='/logout'">Logout</button></div>
<p id="urls" style="background:white;padding:10px;border-radius:8px;font-size:13px"></p>
<input id="search" placeholder="🔍 Search Name e.g JOHN..." oninput="render()">
<h3 id="summary"></h3>
<table><tr><th>✅</th><th>Name</th><th>Amount</th><th>Send / Received</th><th>Time</th></tr><tbody id="list"></tbody></table>
<script>
let allData=[]; let totals={received:0,sent:0}; let shop={};
async function loadData(){ let r=await fetch('/api/my-transactions'); let j=await r.json(); allData=j.transactions; totals={received:j.total_received,sent:j.total_sent}; shop=j.shop; document.getElementById('shop_title').innerText=shop.shop_name+' - Till '+shop.till; document.getElementById('urls').innerHTML='<b>Your Daraja URLs:</b><br>Confirmation: '+j.confirmation_url+'<br>Validation: '+j.validation_url; render(); }
function render(){ let search=document.getElementById('search').value.toLowerCase().trim(); let filtered=allData.filter(t=>{ if(!search) return true; return t.name.toLowerCase().includes(search)||t.phone.includes(search)||t.code.toLowerCase().includes(search); }); document.getElementById('summary').innerText='Received: KES '+totals.received+' | Sent: KES '+totals.sent+' | Showing: '+filtered.length+' / '+allData.length; let html=''; filtered.forEach(t=>{ let cls=t.type=='RECEIVED'?'received':'sent'; let tick=t.confirmed?'✅':'⬜'; let btnCls=t.confirmed?'tick-btn done':'tick-btn'; let rowCls=t.confirmed?'confirmed-row':''; html+='<tr class="'+rowCls+'"><td><button class="'+btnCls+'" onclick="confirmTx('+t.id+',this)">'+tick+'</button></td><td><b>'+t.name+'</b><br><small>'+t.phone+' - '+t.code+'</small></td><td>KES '+t.amount+'</td><td class="'+cls+'">'+t.type+'</td><td>'+t.time+'</td></tr>'; }); document.getElementById('list').innerHTML=html||'<tr><td colspan=5>No transactions yet. Pay to Till to see here.</td></tr>'; }
async function confirmTx(id,btn){ btn.innerText=btn.innerText==='✅'?'⬜':'✅'; btn.classList.toggle('done'); btn.closest('tr').classList.toggle('confirmed-row'); await fetch('/api/confirm?id='+id,{method:'POST'}); await loadData(); }
loadData(); setInterval(loadData,10000);
</script></body></html>
'''

@app.route('/')
def home(): return render_template_string(LOGIN_HTML)
@app.route('/signup')
def signup_page(): return render_template_string(SIGNUP_HTML)
@app.route('/dashboard')
def dashboard():
    if 'till' not in session: return redirect('/')
    return render_template_string(DASHBOARD_HTML)
@app.route('/logout')
def logout(): session.clear(); return redirect('/')

# ---------- AUTH ----------
@app.route('/api/signup', methods=['POST'])
def api_signup():
    d=request.get_json(); shops=load_shops()
    till=str(d.get('till','')).strip()
    if not till or not d.get('shop_name') or not d.get('pw'): return jsonify({'ok':False,'error':'Fill all fields'})
    if till in shops: return jsonify({'ok':False,'error':'Till already registered. Login instead.'})
    shops[till]={'shop_name':d['shop_name'],'owner':d.get('owner',''),'till':till,'password':hash_pw(d['pw']),'created':datetime.now().strftime('%Y-%m-%d')}
    save_shops(shops)
    base=request.host_url.rstrip('/')
    return jsonify({'ok':True,'confirmation_url':f'{base}/api/confirmation/{till}','validation_url':f'{base}/api/validation/{till}'})

@app.route('/api/login', methods=['POST'])
def api_login():
    d=request.get_json(); shops=load_shops(); till=str(d.get('till','')).strip()
    shop=shops.get(till)
    if not shop or shop['password']!=hash_pw(d.get('pw','')): return jsonify({'ok':False,'error':'Wrong Till or Password'})
    session['till']=till; return jsonify({'ok':True})

@app.route('/api/my-transactions')
def my_tx():
    if 'till' not in session: return jsonify({'error':'Not logged in'}),401
    till=session['till']; shops=load_shops(); shop=shops.get(till,{})
    txs=[t for t in load_tx() if str(t.get('till'))==str(till)]
    base=request.host_url.rstrip('/')
    return jsonify({'shop':shop,'transactions':txs,'total_received':sum(t['amount'] for t in txs if t['type']=='RECEIVED'),'total_sent':sum(t['amount'] for t in txs if t['type']=='SENT'),'confirmation_url':f'{base}/api/confirmation/{till}','validation_url':f'{base}/api/validation/{till}'})

@app.route('/api/confirm', methods=['POST'])
def confirm():
    if 'till' not in session: return jsonify({'ok':False}),401
    tx_id=int(request.args.get('id',0)); data=load_tx()
    for t in data:
        if t['id']==tx_id and str(t['till'])==str(session['till']): t['confirmed']=not t['confirmed']
    save_tx(data); return jsonify({'ok':True})

# ---------- SAFARICOM ----------
@app.route('/api/confirmation/<till>', methods=['POST'])
def confirmation(till):
    d=request.get_json(); print(f'PAYMENT TILL {till}:',d)
    try:
        name=((d.get('FirstName','')+' '+d.get('LastName','')).strip().upper() or 'UNKNOWN')
        data=load_tx(); code=d.get('TransID','')
        if not any(t['code']==code for t in data):
            data.append({'id':max([t['id'] for t in data],default=0)+1,'name':name,'phone':d.get('MSISDN',''),'amount':float(d.get('TransAmount',0)),'type':'RECEIVED','code':code,'time':datetime.now().strftime('%H:%M %d-%m-%Y'),'till':str(till),'confirmed':False})
            save_tx(data)
    except Exception as e: print('Error:',e)
    return jsonify({'ResultCode':0,'ResultDesc':'Accepted'})

@app.route('/api/validation/<till>', methods=['POST'])
def validation(till): return jsonify({'ResultCode':0,'ResultDesc':'Accepted'})

if __name__ == '__main__':
    port=int(os.environ.get('PORT',5000))
    app.run(host='0.0.0.0', port=port)
