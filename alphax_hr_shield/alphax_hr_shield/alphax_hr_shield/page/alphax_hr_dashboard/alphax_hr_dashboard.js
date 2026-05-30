frappe.pages["alphax-hr-dashboard"].on_page_load = function (wrapper) {
  const page = frappe.ui.make_app_page({ parent: wrapper, title: "AlphaX HR Shield", single_column: true });
  const $body = $(wrapper).find(".layout-main-section");
  $body.html(`
    <div class="ax-shell">
      <div class="ax-hero">
        <div class="ax-brand"><span class="ax-logo">A</span><div><div class="ax-brand-name">AlphaX <b>HR Shield</b></div><div class="ax-brand-sub">KSA Workforce Compliance Suite</div></div></div>
        <div class="ax-hero-kpis" id="ax-hero-kpis"></div>
      </div>
      <div class="ax-tabs">
        <button class="ax-tab ax-active" data-tab="compliance">Compliance</button>
        <button class="ax-tab" data-tab="nitaqat">Saudization</button>
        <button class="ax-tab" data-tab="esb">End of Service</button>
        <button class="ax-tab" data-tab="gosi">GOSI</button>
        <button class="ax-tab" data-tab="report">التقرير الشامل</button>
        <button class="ax-tab" data-tab="trend">Trend</button>
      </div>
      <div class="ax-panel" id="ax-panel"><div class="ax-loading">Loading…</div></div>
    </div>`);
  page.set_primary_action("Refresh", () => loadAll(), "refresh");

  const COLORS = { expired:"#ef4444", critical:"#f97316", warning:"#eab308", ok:"#10b981", missing:"#8b5cf6" };
  const esc = frappe.utils.escape_html;
  let DASH = null, NIT = null;

  function pill(s){ return `<span class="ax-pill" style="background:${COLORS[s]}22;color:${COLORS[s]}">${s}</span>`; }

  function heroKpis(){
    if(!DASH) return;
    $("#ax-hero-kpis").html(`
      <div class="ax-kpi"><div class="ax-kpi-n">${DASH.total_employees}</div><div class="ax-kpi-l">Employees</div></div>
      <div class="ax-kpi"><div class="ax-kpi-n">${DASH.expiring.length}</div><div class="ax-kpi-l">Flagged Docs</div></div>
      <div class="ax-kpi"><div class="ax-kpi-n">${NIT? NIT.saudization_pct+'%':'—'}</div><div class="ax-kpi-l">Saudization</div></div>
      <div class="ax-kpi"><div class="ax-kpi-n" style="color:${NIT?NIT.band_color:'#fff'}">${NIT?NIT.band_label:'—'}</div><div class="ax-kpi-l">Nitaqat Band</div></div>`);
  }

  const TABS = {
    compliance(){
      const cards = DASH.by_doc_type.map(d=>{
        const total=d.expired+d.critical+d.warning+d.ok+d.missing, bad=d.expired+d.critical;
        const seg=["expired","critical","warning","ok","missing"].map(s=>d[s]?`<span style="flex:${d[s]};background:${COLORS[s]}"></span>`:"").join("");
        return `<div class="ax-card ax-card-grad"><div class="ax-card-t">${esc(d.label)}</div><div class="ax-card-n">${bad}</div><div class="ax-card-s">need attention / ${total} tracked</div><div class="ax-bar">${seg}</div></div>`;
      }).join("");
      const rows = DASH.expiring.slice(0,150).map(r=>`<tr><td>${esc(r.employee_name||r.employee_id)}</td><td>${esc(r.department||"")}</td><td>${esc(r.doc_label)}</td><td>${r.expiry_date||"—"}</td><td style="text-align:right">${r.days_until_expiry<=-9999?"—":r.days_until_expiry}</td><td>${pill(r.status)}</td></tr>`).join("");
      return `<div class="ax-cards">${cards}</div><div class="ax-table-wrap"><div class="ax-table-t">Expiring & Expired Documents</div><table class="ax-table"><thead><tr><th>Employee</th><th>Department</th><th>Document</th><th>Expiry</th><th style="text-align:right">Days</th><th>Status</th></tr></thead><tbody>${rows||'<tr><td colspan=6 style="text-align:center;padding:28px">All clear — nothing expiring.</td></tr>'}</tbody></table></div>`;
    },
    nitaqat(){
      const bands=(NIT.bands||[]).slice().sort((a,b)=>(b.min_percent||0)-(a.min_percent||0));
      const scale = bands.map(b=>`<div class="ax-band ${NIT.band===b.band_name?'ax-band-on':''}" style="--bc:${NIT.band===b.band_name?NIT.band_color:'#cbd5e1'}"><span>${esc(b.band_name)}</span><b>${b.min_percent}%</b></div>`).join("");
      return `<div class="ax-nq"><div class="ax-nq-big" style="background:linear-gradient(135deg,${NIT.band_color},${NIT.band_color}cc)">
          <div class="ax-nq-pct">${NIT.weighted_pct}%</div><div class="ax-nq-band">${esc(NIT.band)}</div>
          <div class="ax-nq-sub">الوزني · النسبة بالعدد: ${NIT.headcount_pct}%</div>
          <div class="ax-nq-sub">${NIT.saudi} سعودي · ${NIT.gcc} خليجي · ${NIT.non_gcc} غير خليجي · الإجمالي ${NIT.total}</div></div>
        <div class="ax-bands">${scale}</div></div>`;
    },
    esb(){
      return `<div class="ax-form"><div class="ax-form-t">End-of-Service Benefit (Labor Law Art. 84 / 85)</div>
        <div class="ax-row"><label>Employee</label><input id="esb-emp" class="ax-in" placeholder="Employee ID (e.g. HR-0001)"></div>
        <div class="ax-row"><label>Last monthly wage (optional)</label><input id="esb-wage" class="ax-in" type="number" placeholder="auto from salary if blank"></div>
        <div class="ax-row"><label>Reason</label><select id="esb-reason" class="ax-in"><option value="termination">Termination / End of contract</option><option value="resignation">Resignation</option></select></div>
        <button class="ax-btn" id="esb-go">Calculate</button><div id="esb-out" class="ax-out"></div></div>`;
    },
    gosi(){
      return `<div class="ax-form"><div class="ax-form-t">GOSI Contributions</div>
        <button class="ax-btn" id="gosi-go">Estimate for all active employees</button>
        <div id="gosi-out" class="ax-out"></div></div>`;
    },
    report(){
      return `<div class="ax-form-t" style="border-radius:12px;border:1px solid var(--border-color);display:flex;justify-content:space-between;align-items:center">
        <span>التقرير الشامل لأوضاع الموظفين (نشط / غير نشط / خروج نهائي / حالة العقود)</span>
        <button class="ax-btn" id="wf-print" style="padding:7px 16px">🖨 طباعة</button></div>
        <div id="wf-out" class="ax-rtl"><div class="ax-loading">جارٍ تحميل التقرير…</div></div>`;
    },
    trend(){
      return `<div class="ax-form"><div class="ax-form-t" style="display:flex;justify-content:space-between;align-items:center">
        <span>Saudization Trend (monthly snapshots)</span>
        <button class="ax-btn" id="tr-snap" style="padding:7px 16px">📸 Capture snapshot now</button></div>
        <div id="tr-out" class="ax-out"><div class="ax-loading">Loading…</div></div></div>`;
    }
  };

  const NAT_AR = {Saudi:"سعودي",Egyptian:"مصري",Indian:"هندي",Bangladeshi:"بنجلاديشي",Nepali:"نيبالي",Pakistani:"باكستاني",Yemeni:"يمني",Filipino:"فلبيني",Djiboutian:"جيبوتي",Unknown:"غير محدد"};
  const natAr = n => NAT_AR[n] || n;

  function renderReport(r){
    const s=r.stats;
    const kpi=(n,l,c)=>`<div class="ax-rkpi" style="--c:${c}"><div class="ax-rkpi-n">${n}</div><div class="ax-rkpi-l">${l}</div></div>`;
    const stats=`<div class="ax-rkpis">
      ${kpi(s.total,"إجمالي الموظفين","#4f46e5")}
      ${kpi(s.saudi+" ("+s.saudi_pct+"%)","سعوديون","#16a34a")}
      ${kpi(s.non_saudi+" ("+s.non_saudi_pct+"%)","غير سعوديين","#06b6d4")}
      ${kpi(s.active+" ("+s.active_pct+"%)","نشطون","#10b981")}
      ${kpi(s.inactive+" ("+s.inactive_pct+"%)","غير نشط / مستبعد","#f59e0b")}
      ${kpi(s.needs_insurance+" ("+s.needs_insurance_pct+"%)","بحاجة تسجيل تأمينات","#8b5cf6")}
      ${kpi(s.final_exit_active_contract+" ("+s.final_exit_active_contract_pct+"%)","خروج نهائي بعقود سارية","#ef4444")}
    </div>`;
    const breakdown=`<div class="ax-rsec-t">توزيع الجنسيات (العمالة الوافدة)</div><div class="ax-nats">`+
      r.nationality_breakdown.map(b=>`<div class="ax-natchip"><b>${b.count}</b> ${natAr(b.nationality)}</div>`).join("")+`</div>`;
    const actions=`<div class="ax-rsec-t">ملخص الإجراءات المطلوب تنفيذها</div><div class="ax-acts">`+
      r.actions.map(a=>`<div class="ax-act"><div class="ax-act-n">${a.n}</div><div class="ax-act-c">${a.count}</div><div class="ax-act-t">${a.title}</div><div class="ax-act-d">${a.desc}</div></div>`).join("")+`</div>`;

    function tbl(title, list, note, danger){
      if(!list || !list.length) return `<div class="ax-rsec-t">${title}</div><div class="ax-empty">لا يوجد سجلات — أو لم يتم ربط الحقول المطلوبة في الإعدادات.</div>`;
      const rows=list.map(e=>`<tr><td>${frappe.utils.escape_html(e.name||e.id)}</td><td>${frappe.utils.escape_html(e.id)}</td><td>${natAr(e.nationality)}</td><td>${e.contract_status||"—"}</td><td>${e.work_permit_status||"—"}</td><td>${e.insurance_status||"—"}</td><td>${e.status||"—"}</td></tr>`).join("");
      return `<div class="ax-rsec-t">${title} <span class="ax-count ${danger?'ax-count-d':''}">${list.length}</span></div>
        ${note?`<div class="ax-note ${danger?'ax-note-d':''}">${note}</div>`:""}
        <table class="ax-table ax-rtable"><thead><tr><th>الاسم</th><th>الهوية/الإقامة</th><th>الجنسية</th><th>العقد</th><th>رخصة العمل</th><th>التأمينات</th><th>الحالة</th></tr></thead><tbody>${rows}</tbody></table>`;
    }
    const sec=r.sections;
    const tables=[
      tbl("العمالة السعودية", sec.saudi_employees),
      tbl("العمالة الوافدة — الوضع الكامل", sec.expat_employees),
      tbl("بحاجة لتسجيل تأمينات", sec.needs_insurance, "موظفون غير مسجلين في نظام التأمينات الاجتماعية — يتطلب مراجعة عاجلة", true),
      tbl("الموظفون المستبعدون / الخروج النهائي", sec.final_exit, "في وضع مستبعد أو خروج نهائي", true),
      tbl("خروج نهائي وعقودهم سارية", sec.final_exit_active_contract, "يستوجب إنهاء العقود وتسوية الأوضاع", true),
      tbl("غير نشطين لكن مسجلون في التأمينات وعقودهم سارية", sec.inactive_insured_active_contract, "يستوجب إيقاف التأمينات وإنهاء العقود", true),
      tbl("بدون عقد أو رخصة عمل", sec.no_contract_or_permit, "وضع مخالف يستوجب التسوية الفورية مع الجهات المختصة", true),
      tbl("رخص عمل منتهية أو مفقودة", sec.expired_or_missing_permit, "يستوجب التجديد الفوري", true),
    ].join("");

    return `<div class="ax-report"><div class="ax-rhead"><div><div class="ax-rtitle">تقرير شامل لأوضاع الموظفين</div><div class="ax-rsub">${r.company?frappe.utils.escape_html(r.company):"AlphaX HR Shield"} — ${new Date().toLocaleDateString('ar-SA')}</div></div><div class="ax-rlogo">AlphaX</div></div>${stats}${breakdown}${actions}${tables}</div>`;
  }

  function bindTab(tab){
    if(tab==="esb"){
      $("#esb-go").on("click",()=>{
        const emp=$("#esb-emp").val(); if(!emp){frappe.msgprint("Enter an Employee ID");return;}
        frappe.call("alphax_hr_shield.api.esb_estimate",{employee:emp,last_wage:$("#esb-wage").val()||null,reason:$("#esb-reason").val()})
          .then(r=>{const d=r.message; $("#esb-out").html(`<div class="ax-result"><div class="ax-result-n">SAR ${frappe.format(d.award,{fieldtype:'Currency'})}</div><div class="ax-result-l">${esc(d.basis)}</div><div class="ax-result-meta">${esc(d.employee_name)} · ${d.years_of_service} yrs · wage ${d.last_wage} · Art.84 base ${d.article84_award} × ${d.applied_fraction}</div></div>`);})
          .catch(e=>$("#esb-out").html(`<div class="ax-err">${esc(e.message||"Error")}</div>`));
      });
    }
    if(tab==="gosi"){
      $("#gosi-go").on("click",()=>{
        $("#gosi-out").html('<div class="ax-loading">Calculating…</div>');
        frappe.call("alphax_hr_shield.api.gosi_run").then(r=>{const d=r.message;
          const rows=d.rows.map(x=>`<tr><td>${esc(x.employee_name)}</td><td>${esc(x.nationality_group)}</td><td style="text-align:right">${x.contributory_wage}</td><td style="text-align:right">${x.employee_contribution}</td><td style="text-align:right">${x.employer_contribution}</td></tr>`).join("");
    if(tab==="report"){
      frappe.call("alphax_hr_shield.api.workforce_report").then(r=>{
        $("#wf-out").html(renderReport(r.message));
        $("#wf-print").on("click",()=>{
          const w=window.open("","_blank");
          w.document.write('<html dir="rtl" lang="ar"><head><meta charset="utf-8"><title>تقرير شامل لأوضاع الموظفين</title>'+
            '<style>body{font-family:Tahoma,Arial,sans-serif;direction:rtl;padding:24px;color:#1e293b}'+
            'table{width:100%;border-collapse:collapse;font-size:12px;margin:10px 0}th,td{border:1px solid #ddd;padding:7px;text-align:right}'+
            'th{background:#f1f5f9}.ax-rsec-t{font-weight:700;font-size:16px;margin:18px 0 6px;border-right:4px solid #7c3aed;padding-right:10px}'+
            '.ax-rkpis{display:flex;flex-wrap:wrap;gap:10px}.ax-rkpi{border:1px solid #e2e8f0;border-radius:10px;padding:10px 16px;min-width:120px}'+
            '.ax-rkpi-n{font-size:20px;font-weight:800}.ax-rkpi-l{font-size:11px;color:#64748b}.ax-note{background:#fff7ed;padding:6px 10px;border-radius:8px;font-size:12px;margin:4px 0}'+
            '.ax-nats,.ax-acts{display:flex;flex-wrap:wrap;gap:8px}.ax-natchip,.ax-act{border:1px solid #e2e8f0;border-radius:8px;padding:8px 12px;font-size:12px}'+
            '.ax-rtitle{font-size:22px;font-weight:800}.ax-rlogo{font-weight:800;color:#7c3aed;font-size:20px}.ax-rhead{display:flex;justify-content:space-between;border-bottom:2px solid #7c3aed;padding-bottom:10px;margin-bottom:14px}</style></head><body>'+
            document.getElementById("wf-out").innerHTML+'</body></html>');
          w.document.close(); w.focus(); setTimeout(()=>w.print(),300);
        });
      }).catch(e=>$("#wf-out").html(`<div class="ax-err">${frappe.utils.escape_html(e.message||"تعذر تحميل التقرير")}</div>`));
    }
    if(tab==="trend"){ loadTrend(); $("#tr-snap").on("click",()=>{ $("#tr-out").html('<div class="ax-loading">Capturing…</div>'); frappe.call("alphax_hr_shield.api.capture_snapshot").then(()=>loadTrend()).catch(e=>$("#tr-out").html(`<div class="ax-err">${esc(e.message||"Error")}</div>`)); }); }
  }

  function loadTrend(){
    frappe.call("alphax_hr_shield.api.get_trend",{limit:24}).then(r=>{
      const rows=r.message||[];
      if(!rows.length){ $("#tr-out").html('<div class="ax-empty" style="margin-top:12px">No snapshots yet — capture one to start tracking the trend.</div>'); return; }
      const max=Math.max(...rows.map(x=>x.weighted_percent||0),10);
      const bars=rows.map(x=>{const h=Math.round((x.weighted_percent||0)/max*120);return `<div class="ax-trbar" title="${x.snapshot_date}: ${x.weighted_percent}%"><div class="ax-trfill" style="height:${h}px"></div><div class="ax-trlbl">${(x.snapshot_date||'').slice(5)}</div><div class="ax-trval">${x.weighted_percent}%</div></div>`;}).join("");
      const tbl=rows.slice().reverse().map(x=>`<tr><td>${x.snapshot_date}</td><td>${x.total_headcount}</td><td>${x.saudi_headcount}</td><td>${x.headcount_percent}%</td><td>${x.weighted_percent}%</td><td>${esc(x.nitaqat_band||'')}</td></tr>`).join("");
      $("#tr-out").html(`<div class="ax-trend">${bars}</div><table class="ax-table"><thead><tr><th>Date</th><th>Total</th><th>Saudi</th><th>Headcount %</th><th>Weighted %</th><th>Band</th></tr></thead><tbody>${tbl}</tbody></table>`);
    }).catch(e=>$("#tr-out").html(`<div class="ax-err">${esc(e.message||"Error")}</div>`));
  }

  function show(tab){ $("#ax-panel").html(TABS[tab]()); bindTab(tab); }

  $body.on("click",".ax-tab",function(){ $(".ax-tab").removeClass("ax-active"); $(this).addClass("ax-active"); show($(this).data("tab")); });

  function loadAll(){
    $("#ax-panel").html('<div class="ax-loading">Loading compliance data…</div>');
    Promise.all([frappe.call("alphax_hr_shield.api.dashboard"),frappe.call("alphax_hr_shield.api.nitaqat")])
      .then(([d,n])=>{DASH=d.message;NIT=n.message;heroKpis();show($(".ax-tab.ax-active").data("tab")||"compliance");})
      .catch(e=>{$("#ax-panel").html('<div class="ax-err">Could not load. Ensure HR/HRMS is installed and you have HR permissions.</div>');console.error(e);});
  }
  loadAll();
};
