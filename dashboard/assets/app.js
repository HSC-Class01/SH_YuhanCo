const fmt=(v,d=0)=>v==null||Number.isNaN(Number(v))?'—':Number(v).toLocaleString('ko-KR',{maximumFractionDigits:d});
const pct=v=>v==null||Number.isNaN(Number(v))?'—':(Number(v)*100).toFixed(1)+'%';
async function csv(path){
  const r=await fetch(path,{cache:'no-store'});
  if(!r.ok) throw new Error(path+' HTTP '+r.status);
  const t=await r.text();
  const rows=t.trim().split(/\r?\n/).map(x=>x.split(/,(?=(?:[^\"]*\"[^\"]*\")*[^\"]*$)/).map(v=>v.replace(/^\"|\"$/g,'').replace(/\"\"/g,'\"')));
  const h=rows.shift();
  return rows.map(row=>Object.fromEntries(h.map((k,i)=>[k,row[i]??''])));
}
const num=(o,k)=>{const n=Number(o[k]);return Number.isFinite(n)?n:null;};
function lineChart(id,labels,datasets,percent=false){return new Chart(document.getElementById(id),{type:'line',data:{labels,datasets},options:{responsive:true,maintainAspectRatio:false,interaction:{mode:'index',intersect:false},plugins:{legend:{labels:{usePointStyle:true,font:{size:10}}}},scales:{x:{grid:{display:false}},y:{beginAtZero:false,ticks:{callback:v=>percent?v+'%':fmt(v)}}}}})}
function table(id,rows,cols){const el=document.getElementById(id);el.innerHTML='<thead><tr>'+cols.map(c=>'<th>'+c.label+'</th>').join('')+'</tr></thead><tbody>'+rows.slice().reverse().map(r=>'<tr>'+cols.map(c=>'<td>'+(c.fn?c.fn(r):r[c.key]??'—')+'</td>').join('')+'</tr>').join('')+'</tbody>'}
(async()=>{
 try{
  const [f,r,p,l]=await Promise.all([csv('data/financials.csv'),csv('data/ratios.csv'),csv('data/peers.csv'),fetch('data/latest.json',{cache:'no-store'}).then(x=>{if(!x.ok)throw new Error('latest.json HTTP '+x.status);return x.json()})]);
  document.getElementById('updatedAt').textContent=new Date(l.updated_at).toLocaleString('ko-KR',{dateStyle:'medium'});
  const annual=r.filter(x=>x.kind==='annual').sort((a,b)=>Number(a.year)-Number(b.year));
  const latest=r.slice().sort((a,b)=>Number(a.year)-Number(b.year)||Number(a.period_order)-Number(b.period_order)).at(-1);
  document.getElementById('kpis').innerHTML=[['최근 매출액',fmt(num(latest,'revenue'))+' 백만원'],['최근 영업이익률',pct(num(latest,'operating_margin'))],['최근 ROE',pct(num(latest,'roe'))],['최근 순차입금',fmt(num(latest,'net_debt'))+' 백만원']].map(x=>'<div class="kpi"><div class="kpi-label">'+x[0]+'</div><div class="kpi-value">'+x[1]+'</div></div>').join('');
  const labels=annual.map(x=>x.year);
  lineChart('profitChart',labels,[{label:'매출액',data:annual.map(x=>num(x,'revenue')),borderWidth:2,tension:.25},{label:'영업이익',data:annual.map(x=>num(x,'operating_income')),borderWidth:2,tension:.25},{label:'순이익',data:annual.map(x=>num(x,'net_income')),borderWidth:2,tension:.25}]);
  lineChart('marginChart',labels,[{label:'매출총이익률',data:annual.map(x=>num(x,'gross_margin')*100),borderWidth:2,tension:.25},{label:'영업이익률',data:annual.map(x=>num(x,'operating_margin')*100),borderWidth:2,tension:.25},{label:'순이익률',data:annual.map(x=>num(x,'net_margin')*100),borderWidth:2,tension:.25}],true);
  lineChart('cashChart',labels,[{label:'CFO',data:annual.map(x=>num(x,'cfo')),borderWidth:2,tension:.25},{label:'FCF',data:annual.map(x=>num(x,'fcf')),borderWidth:2,tension:.25}]);
  lineChart('balanceChart',labels,[{label:'총자산',data:annual.map(x=>num(x,'assets')),borderWidth:2,tension:.25},{label:'총부채',data:annual.map(x=>num(x,'liabilities')),borderWidth:2,tension:.25},{label:'자본',data:annual.map(x=>num(x,'equity')),borderWidth:2,tension:.25}]);
  lineChart('ratioChart',labels,[{label:'유동비율',data:annual.map(x=>num(x,'current_ratio')),borderWidth:2,tension:.25},{label:'부채비율',data:annual.map(x=>num(x,'debt_ratio')),borderWidth:2,tension:.25},{label:'자기자본비율',data:annual.map(x=>num(x,'equity_ratio')),borderWidth:2,tension:.25}]);
  const cols=[{key:'year',label:'연도'},{key:'period_label',label:'기간'},{key:'revenue',label:'매출액',fn:x=>fmt(num(x,'revenue'))},{key:'gross_profit',label:'매출총이익',fn:x=>fmt(num(x,'gross_profit'))},{key:'operating_income',label:'영업이익',fn:x=>fmt(num(x,'operating_income'))},{key:'net_income',label:'당기순이익',fn:x=>fmt(num(x,'net_income'))},{key:'cfo',label:'영업현금흐름',fn:x=>fmt(num(x,'cfo'))},{key:'fcf',label:'FCF',fn:x=>fmt(num(x,'fcf'))},{key:'operating_margin',label:'영업이익률',fn:x=>pct(num(x,'operating_margin'))},{key:'roe',label:'ROE',fn:x=>pct(num(x,'roe'))},{key:'current_ratio',label:'유동비율',fn:x=>{const n=num(x,'current_ratio');return n==null?'—':n.toFixed(2)}},{key:'debt_ratio',label:'부채비율',fn:x=>{const n=num(x,'debt_ratio');return n==null?'—':n.toFixed(2)}}];
  table('annualTable',r.filter(x=>x.kind==='annual'),cols);
  table('halfTable',r.filter(x=>x.kind==='half_year'),cols);
  table('quarterTable',r.filter(x=>x.kind==='q1'||x.kind==='q3'),cols);
  table('peerTable',p,[{key:'name',label:'기업'},{key:'stock_code',label:'종목코드'},{label:'비교 기준',fn:()=> '국내 상장 제약사 · 사업구조/매출 규모 비교군'}]);
 }catch(e){console.error('Dashboard data loading error:',e);document.getElementById('updatedAt').textContent='데이터 로딩 오류';document.getElementById('kpis').innerHTML='<div class="kpi"><div class="kpi-label">상태</div><div class="kpi-value">데이터 확인 필요</div></div>';}
})();