const state={ui:null,backendMap:null,catalog:null,icons:[],entities:[],ldrVoltage:null,deviceBrightness:null,deviceMode:null,deviceNight:null,deviceTouchCalibration:null,touchCalibrationWaiting:false,touchCalibrationBaseline:null,selectedPage:0,editingSettings:false,editingReminder:false,scheduledReminders:[],reminderScheduleAt:"",reminderRepeat:"once",reminderWeekdays:[],reminderDraft:{reminder_id:"aviso_manual",title:"Recordatorio",message:"",level:"reminder",sound_mode:"once",alarm_duration:120,snooze_minutes:0},collapsed:new Set()};
const $=s=>document.querySelector(s), pageList=$("#pageList"),pageForm=$("#pageForm"),controlList=$("#controlList"),preview=$("#devicePreview"),validationBox=$("#validationBox"),saveButton=$("#saveButton");
const clone=v=>JSON.parse(JSON.stringify(v));
const slug=t=>String(t||"control").toLowerCase().normalize("NFD").replace(/[\u0300-\u036f]/g,"").replace(/[^a-z0-9]+/g,"_").replace(/^_|_$/g,"").slice(0,38)||"control";
let datalistSequence=0,ldrPollingTimer=null;

// Climate and cover use fixed, purpose-built layouts in LVGL. Keep their
// editor preview on the same 320 x 240 geometry instead of showing a generic grid.
const defaultRenderPreview=renderPreview;
renderPreview=function renderRichPreview(){
  if(state.editingReminder)return renderReminderPreview();
  if(state.editingSettings)return renderSettingsPreview();
  const page=state.ui.pages[state.selectedPage];
  if(!["button_grid","sensor_grid","clock_weather","climate","cover","media"].includes(page.template))return defaultRenderPreview();
  const screen=document.createElement("div");
  const label=(role,fallback)=>page.controls.find(control=>control.role===role)?.caption||fallback;
  screen.className=`screen ${state.ui.settings?.appearance?.mode||"dark"} accent-${state.ui.settings?.appearance?.accent||"mint"}`;
  if(page.template==="button_grid"){
    const columns=page.controls.length===2?2:page.controls.length===4?2:3;
    screen.innerHTML='<div class="template-face button-grid-face"><strong class="template-title"></strong><span class="template-arrow previous">&#8249;</span><span class="template-arrow next">&#8250;</span><div class="button-preview-grid"></div></div>';
    screen.querySelector(".template-title").textContent=page.title||"Sin titulo";
    const grid=screen.querySelector(".button-preview-grid");
    grid.classList.add(`columns-${columns}`);
    page.controls.forEach(control=>{const mapping=state.backendMap.controls[control.id]||{},button=document.createElement("div"),icon=document.createElement("i"),caption=document.createElement("span"),iconName=mapping.domain==="binary_sensor"?(control.icon_off||control.icon):(control.icon||"");button.className="button-preview-cell";button.style.borderColor=control.color;button.style.background=`${control.color}44`;icon.className="preview-mdi";icon.textContent=iconGlyph(iconName);icon.classList.toggle("hidden",!icon.textContent);caption.textContent=control.caption;button.append(icon,caption);grid.append(button)});
  }else if(page.template==="sensor_grid"){
    screen.innerHTML='<div class="template-face sensor-grid-face"><strong class="template-title"></strong><span class="template-arrow previous">&#8249;</span><span class="template-arrow next">&#8250;</span><div class="sensor-preview-grid"></div></div>';
    screen.querySelector(".template-title").textContent=page.title||"Sin titulo";
    const grid=screen.querySelector(".sensor-preview-grid");
    page.controls.forEach(control=>{const mapping=state.backendMap.controls[control.id]||{},card=document.createElement("div"),caption=document.createElement("span"),reading=document.createElement("div"),icon=document.createElement("i"),value=document.createElement("b"),iconName=mapping.domain==="binary_sensor"?(control.icon_off||control.icon):(control.icon||"");card.className="sensor-preview-cell";card.style.borderColor=control.color;caption.textContent=control.caption;icon.className="preview-mdi";icon.textContent=iconGlyph(iconName);icon.classList.toggle("hidden",!icon.textContent);value.textContent=mapping.domain==="binary_sensor"?(mapping.value_map?.off||"Inactivo"):`--${control.unit?` ${control.unit}`:""}`;reading.append(icon,value);card.append(caption,reading);grid.append(card)});
  }else if(page.template==="clock_weather"){
    screen.innerHTML='<div class="clock-face"><div class="clock-time">10:42</div><div class="clock-date">Miércoles 29 de julio</div><div class="clock-condition">Despejado</div><div class="clock-temperature">21.5 C</div><div class="clock-humidity">Humedad 58 %</div><small>Toca para volver</small></div>';
    // Keep the editor preview aligned with the actual screensaver: it has no
    // interaction hint and includes the same small weather glyph.
    screen.querySelector("small")?.remove();
    const weatherIcon=document.createElement("i");
    weatherIcon.className="preview-mdi clock-weather-icon";
    weatherIcon.textContent=iconGlyph("mdi:weather-sunny");
    screen.querySelector(".clock-face").append(weatherIcon);
  }else if(page.template==="climate"){
    screen.innerHTML='<div class="template-face climate-face"><strong class="template-title"></strong><span class="template-arrow previous">&#8249;</span><span class="template-arrow next">&#8250;</span><div class="climate-current">Actual: 21.0 C</div><div class="climate-target">Objetivo: 22.0 C</div><button class="climate-decrease"></button><button class="climate-power"></button><button class="climate-increase"></button></div>';
    screen.querySelector(".template-title").textContent=page.title||"Sin titulo";
    screen.querySelector(".climate-decrease").textContent=label("decrease","-");
    screen.querySelector(".climate-power").textContent=label("power","Encender");
    screen.querySelector(".climate-increase").textContent=label("increase","+");
  }else if(page.template==="cover"){
    screen.innerHTML='<div class="template-face cover-face"><strong class="template-title"></strong><span class="template-arrow previous">&#8249;</span><span class="template-arrow next">&#8250;</span><div class="cover-position">50 %</div><div class="cover-state">Posicion conocida</div><button class="cover-open"></button><button class="cover-close"></button><button class="cover-close-step"></button><button class="cover-open-step"></button></div>';
    screen.querySelector(".template-title").textContent=page.title||"Sin titulo";
    screen.querySelector(".cover-open").textContent=label("open","Abrir");
    screen.querySelector(".cover-close").textContent=label("close","Cerrar");
    screen.querySelector(".cover-close-step").textContent=label("close_step","-10 %");
    screen.querySelector(".cover-open-step").textContent=label("open_step","+10 %");
  }else{
    screen.innerHTML='<div class="template-face media-face"><strong class="template-title"></strong><span class="template-arrow previous">&#8249;</span><span class="template-arrow next">&#8250;</span><div class="media-artwork">IMG</div><button class="media-player">Reproductor <span>⌄</span></button><div class="media-title">Canción o emisora muy larga...</div><div class="media-artist">Artista</div><div class="media-station">Emisora</div><div class="media-volume">Vol 42 %</div><div class="media-volume-bar"><span></span></div><button class="media-previous">Anterior</button><button class="media-play">Play/Pausa</button><button class="media-next">Siguiente</button><button class="media-vol-down">Vol -</button><button class="media-vol-up">Vol +</button></div>';
    screen.querySelector(".template-title").textContent=page.title||"Multimedia";
    [[".media-previous","mdi:skip-previous"],[".media-play","mdi:play"],[".media-next","mdi:skip-next"],[".media-vol-down","mdi:volume-minus"],[".media-vol-up","mdi:volume-plus"]].forEach(([selector,name])=>{const button=screen.querySelector(selector);button.textContent=iconGlyph(name);button.classList.add("preview-mdi")});
  }
  preview.replaceChildren(screen);
};

function iconChoices(current=""){const choices=[{value:"",label:"Sin ícono"}],seen=new Set();state.icons.forEach(icon=>{seen.add(icon.name);choices.push({value:icon.name,label:`${icon.label} · ${icon.name}`})});if(current&&!seen.has(current))choices.splice(1,0,{value:current,label:`${current} (actual)`});return choices}
function iconGlyph(name){const item=state.icons.find(icon=>icon.name===name);return item?String.fromCodePoint(parseInt(item.codepoint,16)):""}
const timeoutChoices=[{value:0,label:"Nunca"},{value:15,label:"15 segundos"},{value:30,label:"30 segundos"},{value:60,label:"1 minuto"},{value:120,label:"2 minutos"},{value:300,label:"5 minutos"},{value:600,label:"10 minutos"},{value:900,label:"15 minutos"},{value:1800,label:"30 minutos"},{value:3600,label:"1 hora"}];
const attributeLabels={current_temperature:"Temperatura actual",temperature:"Temperatura objetivo",humidity:"Humedad",current_position:"Posición actual",brightness:"Brillo",battery_level:"Nivel de batería",hvac_action:"Actividad actual",percentage:"Porcentaje",pressure:"Presión",illuminance:"Iluminación"};
function attributeChoices(entityId,current=""){const entity=state.entities.find(item=>item.entity_id===entityId),choices=[{value:"",label:`Estado principal${entity?` · ${entity.state}`:""}`}],seen=new Set();if(entity)entity.attributes.forEach(name=>{seen.add(name);const value=entity.attribute_values?.[name],sample=value===undefined?"":` · ${String(value).slice(0,35)}`;choices.push({value:name,label:`${attributeLabels[name]||name}${sample}`})});if(current&&!seen.has(current))choices.splice(1,0,{value:current,label:`${attributeLabels[current]||current} (actual)`});return choices}
function actionChoices(mapping,control){const domain=mapping.domain||"",single=(value,label)=>[{value,label}];if(control.action==="decrement")return single("decrement","Bajar temperatura");if(control.action==="increment")return single("increment","Subir temperatura");if(["open","close","open_step","close_step"].includes(control.action))return single(control.action,{open:"Abrir completamente",close:"Cerrar completamente",open_step:"Abrir parcialmente",close_step:"Cerrar parcialmente"}[control.action]);if(["previous","play_pause","next","volume_down","volume_up"].includes(control.action))return single(control.action,{previous:"Pista anterior",play_pause:"Reproducir o pausar",next:"Pista siguiente",volume_down:"Bajar volumen",volume_up:"Subir volumen"}[control.action]);if(domain==="scene")return single("activate","Activar escena");if(domain==="script")return single("run","Ejecutar script");if(domain==="button")return single("press","Pulsar botón");return [{value:"toggle",label:"Alternar encendido/apagado"},{value:"turn_on",label:"Encender"},{value:"turn_off",label:"Apagar"}]}
function setControlAction(control,mapping,action){control.action=action;mapping.action=action;const aliases={activate:"turn_on",run:"turn_on"};if(mapping.domain==="climate"&&control.role==="power"&&action==="toggle")mapping.service="toggle_hvac";else if(aliases[action])mapping.service=aliases[action];else if(!["decrement","increment","open","close","open_step","close_step"].includes(action))delete mapping.service}

function ensureSettings(){
  const legacy=state.ui.screensaver_timeout??30;
  state.ui.settings||={};
  const fill=(target,defaults)=>{for(const[key,value]of Object.entries(defaults))if(target[key]===undefined)target[key]=value};
  state.ui.settings.display||={};fill(state.ui.settings.display,{brightness:100,auto_brightness:false,minimum_brightness:15,maximum_brightness:100,ldr_dark_voltage:3,ldr_bright_voltage:.2});
  state.ui.settings.appearance||={};fill(state.ui.settings.appearance,{mode:"dark",accent:"mint"});
  state.ui.settings.inactivity||={};fill(state.ui.settings.inactivity,{timeout:legacy,mode:"clock_weather",dim_brightness:10});
  state.ui.settings.night||={};fill(state.ui.settings.night,{enabled:false,start:"23:00",end:"07:00",brightness:15,mode:"screen_off"});
  state.ui.settings.sound||={};fill(state.ui.settings.sound,{enabled:true,volume:5,touch:true,navigation:true,notifications:true,mute_at_night:false});fill(state.ui.settings.sound,{touch_volume:state.ui.settings.sound.volume,navigation_volume:state.ui.settings.sound.volume,notification_volume:state.ui.settings.sound.volume});
  state.ui.settings.touchscreen||={};fill(state.ui.settings.touchscreen,{x_min:200,x_max:3700,y_min:240,y_max:3800});
  state.ui.screensaver_timeout=state.ui.settings.inactivity.timeout;
}

function showToast(message,error=false){const toast=$("#toast");toast.textContent=message;toast.className=`toast${error?" error":""}`;clearTimeout(showToast.timer);showToast.timer=setTimeout(()=>toast.classList.add("hidden"),4200)}
async function api(path,options={}){const response=await fetch(path,{headers:{"Content-Type":"application/json",...(options.headers||{})},...options});const payload=await response.json();if(!response.ok)throw new Error(payload.error||(payload.errors||[]).join("\n")||`Error ${response.status}`);return payload}
function uniqueId(base){const used=new Set(state.ui.pages.flatMap(p=>p.controls.map(c=>c.id)));let candidate=slug(base),suffix=2;while(used.has(candidate))candidate=`${slug(base)}_${suffix++}`;return candidate}
function defaultMapping(control){
  const mapping={entity_id:""},role=control.role||"",action=control.action||"";
  if(control.type==="value")mapping.value_only=true;
  if(role==="current_temperature"){mapping.attribute="current_temperature";mapping.decimals=1;delete mapping.value_only}
  if(role==="target_temperature"){mapping.attribute="temperature";mapping.decimals=1;delete mapping.value_only}
  if(role==="position"){mapping.attribute="current_position";mapping.decimals=0;delete mapping.value_only}
  if(role==="outside_temperature"){mapping.attribute="temperature";mapping.decimals=1;delete mapping.value_only}
  if(role==="humidity"){mapping.attribute="humidity";mapping.decimals=0;delete mapping.value_only}
  if(role==="state"){mapping.value_map={open:"Abierta",closed:"Cerrada",opening:"Abriendo",closing:"Cerrando"}}
  if(role==="player"){mapping.attribute="friendly_name";delete mapping.value_only}
  if(role==="title"){mapping.attribute="media_title";delete mapping.value_only}
  if(role==="artist"){mapping.attribute="media_artist";delete mapping.value_only}
  if(role==="station"){mapping.attribute="media_album_name";delete mapping.value_only}
  if(role==="volume"){mapping.attribute="volume_level";mapping.scale=100;mapping.decimals=0;delete mapping.value_only}
  if(control.type==="button"){
    mapping.action=action||"toggle";mapping.allow_control=role!=="power";
    if(action==="decrement"||action==="increment"){mapping.service="set_temperature";mapping.temperature_delta=action==="decrement"?-1:1;mapping.publish_state=false}
    if(action==="open"){mapping.service="open_cover";mapping.publish_state=false}
    if(action==="close"){mapping.service="close_cover";mapping.publish_state=false}
    if(action==="close_step"||action==="open_step"){mapping.service="set_cover_position";mapping.position_delta=action==="close_step"?-10:10;mapping.publish_state=false}
    if(role==="power"){mapping.state_active=true;delete mapping.action}
    const mediaServices={previous:"media_previous_track",play_pause:"media_play_pause",next:"media_next_track",volume_down:"volume_down",volume_up:"volume_up"};
    if(mediaServices[action]){mapping.service=mediaServices[action];mapping.allow_control=true;mapping.publish_state=false}
    if(role==="play_pause"){mapping.active_states=["playing","buffering"];delete mapping.publish_state}
  }
  return mapping;
}
function makeControl(templateName,source,index){const role=source.role||"",caption=source.caption||`Control ${index+1}`,type=source.type||"button";const control={type,id:uniqueId(`${templateName}_${role||index+1}`),caption,color:type==="button"?"#1976D2":"#FFFFFF",meta:{}};if(role)control.role=role;if(source.action)control.action=source.action;if(type==="value")control.unit="";state.backendMap.controls[control.id]=defaultMapping(control);return control}
function makePage(templateName="button_grid"){const spec=state.catalog[templateName],variant=Object.keys(spec.variants)[0],page={template:templateName,variant,title:spec.screensaver?"":"Nueva página",controls:[]};if(spec.screensaver)page.screensaver=true;const cs=spec.controls;const sources=cs.kind==="fixed"?cs.roles:Array.from({length:cs.kind==="variable"?cs.minimum:spec.variants[variant]},(_,i)=>({type:cs.type,caption:`Control ${i+1}`}));page.controls=sources.map((s,i)=>makeControl(templateName,s,i));return page}
function removeMappings(page){page.controls.forEach(c=>delete state.backendMap.controls[c.id])}
function resetControlsForTemplate(page,templateName,variant=null){removeMappings(page);const replacement=makePage(templateName);page.template=templateName;page.variant=variant||replacement.variant;page.controls=replacement.controls;if(replacement.screensaver){page.screensaver=true;page.title=""}else{delete page.screensaver;if(!page.title)page.title="Nueva página"}if(templateName==="media")page.controls.forEach(control=>state.collapsed.add(control.id));if(state.catalog[templateName].controls.kind==="repeated")resizeRepeatedControls(page)}
function resizeRepeatedControls(page){const spec=state.catalog[page.template];if(spec.controls.kind!=="repeated")return;const count=spec.variants[page.variant];while(page.controls.length>count){const removed=page.controls.pop();delete state.backendMap.controls[removed.id]}while(page.controls.length<count)page.controls.push(makeControl(page.template,{type:spec.controls.type,caption:`Control ${page.controls.length+1}`},page.controls.length))}

function inputField(label,value,onChange,options={}){const field=document.createElement("div");field.className=`field${options.wide?" wide":""}`;const caption=document.createElement("label");caption.textContent=label;let input,extra=null;if(options.choices&&options.searchable){input=document.createElement("input");input.type="search";input.value=value??"";input.placeholder=options.placeholder||"Escribí para buscar…";input.autocomplete="off";const results=document.createElement("select");results.className="search-results";results.size=5;const renderResults=()=>{const query=input.value.trim().toLocaleLowerCase();const matches=options.choices.filter(choice=>!query||`${choice.label} ${choice.value}`.toLocaleLowerCase().includes(query));results.replaceChildren();if(!matches.length){const empty=document.createElement("option");empty.disabled=true;empty.textContent="Sin coincidencias";results.append(empty);return}matches.slice(0,80).forEach(choice=>{const option=document.createElement("option");option.value=choice.value;option.textContent=choice.label;option.selected=String(choice.value)===String(value);results.append(option)})};input.addEventListener("input",renderResults);input.addEventListener("change",()=>{const exact=options.choices.find(choice=>choice.value===input.value);if(exact||input.value==="")onChange(input.value)});results.addEventListener("change",()=>{input.value=results.value;onChange(results.value)});renderResults();extra=results}else if(options.choices){input=document.createElement("select");options.choices.forEach(o=>{const option=document.createElement("option");option.value=o.value;option.textContent=o.label;option.selected=String(o.value)===String(value);input.append(option)})}else{input=document.createElement("input");input.type=options.type||"text";input.value=value??"";if(options.placeholder)input.placeholder=options.placeholder;if(options.min!==undefined)input.min=options.min;if(options.max!==undefined)input.max=options.max;if(options.step!==undefined)input.step=options.step}input.disabled=Boolean(options.disabled);if(!input.disabled&&!options.searchable){const eventName=options.event||"input",handler=()=>onChange(options.type==="number"&&input.value!==""?Number(input.value):input.value);input.addEventListener(eventName,handler);if(eventName!=="change")input.addEventListener("change",handler)}field.append(caption,input);if(extra)field.append(extra);return field}
function renderPages(){
  pageList.replaceChildren();
  state.ui.pages.forEach((page,index)=>{
    const card=document.createElement("div");
    card.className=`page-card${!state.editingSettings&&!state.editingReminder&&index===state.selectedPage?" active":""}`;
    card.draggable=true;card.dataset.index=index;
    card.innerHTML=`<span class="page-number">${page.screensaver?"◐":index+1}</span><div class="page-name"><strong></strong><span></span></div>`;
    card.querySelector("strong").textContent=page.title||(page.screensaver?"Protector de pantalla":"Sin título");
    card.querySelector(".page-name span").textContent=state.catalog[page.template]?.label||page.template;
    card.onclick=()=>{state.editingSettings=false;state.editingReminder=false;state.selectedPage=index;renderAll()};
    card.ondragstart=()=>card.classList.add("dragging");card.ondragend=()=>card.classList.remove("dragging");card.ondragover=e=>e.preventDefault();
    card.ondrop=e=>{e.preventDefault();const from=Number(pageList.querySelector(".dragging")?.dataset.index);if(!Number.isInteger(from)||from===index)return;const[moved]=state.ui.pages.splice(from,1);state.ui.pages.splice(index,0,moved);state.selectedPage=index;renderAll()};
    pageList.append(card)
  });
  $("#deviceSettingsButton").classList.toggle("active",state.editingSettings);
  $("#reminderCenterButton").classList.toggle("active",state.editingReminder);
}
function renderPageForm(){const page=state.ui.pages[state.selectedPage],screensaver=page.template==="clock_weather"&&page.variant==="screensaver";$("#editorTitle").textContent=screensaver?"Protector de pantalla":page.title;pageForm.replaceChildren();const fields=[];if(!screensaver)fields.push(inputField("Título",page.title,v=>{page.title=v;renderPages();renderPreview();validate()},{wide:true}));fields.push(inputField("Template",page.template,v=>{resetControlsForTemplate(page,v);renderAll()},{choices:Object.entries(state.catalog).map(([value,item])=>({value,label:item.label})),event:"change"}),inputField("Variante",page.variant,v=>{page.variant=v;resizeRepeatedControls(page);renderAll()},{choices:Object.keys(state.catalog[page.template].variants).map(value=>({value,label:value.replaceAll("_"," ")})),event:"change"}));if(screensaver)fields.push(inputField("Activar protector después de",state.ui.settings.inactivity.timeout,v=>{state.ui.settings.inactivity.timeout=v;state.ui.screensaver_timeout=v;validate()},{choices:timeoutChoices,event:"change",type:"number",wide:true}));pageForm.append(...fields);if(page.template==="media")renderMediaPlayerFields(page);$("#addControlButton").classList.toggle("hidden",state.catalog[page.template].controls.kind!=="variable"||page.controls.length>=4)}

function renderMediaPlayerFields(page){
  const selector=page.controls.find(control=>control.role==="player"),selectorMap=state.backendMap.controls[selector.id]||=defaultMapping(selector),players=Array.isArray(selectorMap.entity_ids)?selectorMap.entity_ids:[selectorMap.entity_id||""];
  const choices=entityChoices("",selector,page);
  const setPlayer=(index,value)=>{const next=[...players];next[index]=value;const clean=next.filter((item,pos)=>item&&next.indexOf(item)===pos);const primary=clean[0]||"";page.controls.forEach(control=>{const mapping=state.backendMap.controls[control.id]||=defaultMapping(control);configureMappingForEntity(control,mapping,primary,page);mapping.media_selector_id=selector.id});const updated=state.backendMap.controls[selector.id];updated.entity_ids=clean;updated.entity_id=primary;renderPageForm();renderControls();renderPreview();validate()};
  const group=document.createElement("section");group.className="settings-section media-player-settings";const heading=document.createElement("div");heading.className="settings-section-heading";heading.innerHTML="<h3>Reproductores</h3><p>El selector de la pantalla cambia entre estos reproductores.</p>";const grid=document.createElement("div");grid.className="settings-grid";for(let index=0;index<3;index++)grid.append(inputField(`Reproductor ${index+1}`,players[index]||"",value=>setPlayer(index,value),{choices,searchable:true,wide:true}));group.append(heading,grid);pageForm.append(group);
}

const yesNoChoices=[{value:"yes",label:"Sí"},{value:"no",label:"No"}];
const idleModeChoices=[{value:"clock_weather",label:"Mostrar reloj y clima"},{value:"screen_off",label:"Apagar pantalla"},{value:"dim",label:"Bajar el brillo"},{value:"none",label:"No hacer nada"}];
function settingsGroup(title,description,fields){const group=document.createElement("section");group.className="settings-section";const header=document.createElement("div");header.className="settings-section-heading";header.innerHTML="<h3></h3><p></p>";header.querySelector("h3").textContent=title;header.querySelector("p").textContent=description;const grid=document.createElement("div");grid.className="settings-grid";grid.append(...fields);group.append(header,grid);return group}
function renderSettings(){
  ensureSettings();
  const {display,appearance,inactivity,night,sound,touchscreen}=state.ui.settings;
  $("#editorTitle").textContent="Configuración del dispositivo";
  $("#duplicateButton").classList.add("hidden");$("#deleteButton").classList.add("hidden");
  $("#controlsHeading").classList.add("hidden");controlList.classList.add("hidden");
  pageForm.classList.add("settings-form");pageForm.replaceChildren();
  const appearanceSection=settingsGroup("Aspecto","Modo base y acento para detalles de navegación.",[
    inputField("Modo",appearance.mode,v=>{appearance.mode=v;renderSettings();renderPreview();validate()},{choices:[{value:"dark",label:"Oscuro"},{value:"light",label:"Claro"}],event:"change"}),
    inputField("Color de acento",appearance.accent,v=>{appearance.accent=v;renderPreview();validate()},{choices:[{value:"mint",label:"Menta"},{value:"blue",label:"Azul"},{value:"violet",label:"Violeta"},{value:"amber",label:"Ámbar"},{value:"rose",label:"Rosa"}],event:"change"})
  ]);
  const manualBrightnessField=inputField("Brillo manual",display.brightness,v=>{display.brightness=v;renderPreview();validate()},{type:"number",min:0,max:100,disabled:display.auto_brightness});
  const ldrDarkField=inputField("LDR en oscuridad (V)",display.ldr_dark_voltage,v=>{display.ldr_dark_voltage=v;validate()},{type:"number",min:0,max:3.3,step:.01});
  const ldrBrightField=inputField("LDR con mucha luz (V)",display.ldr_bright_voltage,v=>{display.ldr_bright_voltage=v;validate()},{type:"number",min:0,max:3.3,step:.01});
  const displaySection=settingsGroup("Pantalla","El brillo manual se usa solo cuando el automático está desactivado. El horario nocturno tiene prioridad sobre ambos.",[
      manualBrightnessField,
      inputField("Brillo automático",display.auto_brightness?"yes":"no",v=>{display.auto_brightness=v==="yes";renderSettings();renderPreview();validate()},{choices:yesNoChoices,event:"change"}),
      inputField("Brillo mínimo automático",display.minimum_brightness,v=>{display.minimum_brightness=v;validate()},{type:"number",min:0,max:100}),
      inputField("Brillo máximo automático",display.maximum_brightness,v=>{display.maximum_brightness=v;validate()},{type:"number",min:0,max:100}),
      ldrDarkField,
      ldrBrightField
    ]);
  pageForm.append(appearanceSection,
    displaySection,
    settingsGroup("Inactividad","Qué hace la pantalla después de un tiempo sin tocarla.",[
      inputField("Tiempo sin uso",inactivity.timeout,v=>{inactivity.timeout=v;state.ui.screensaver_timeout=v;validate()},{choices:timeoutChoices,event:"change",type:"number"}),
      inputField("Al quedar inactiva",inactivity.mode,v=>{inactivity.mode=v;renderSettings();renderPreview();validate()},{choices:idleModeChoices,event:"change"}),
      inputField("Brillo tenue",inactivity.dim_brightness,v=>{inactivity.dim_brightness=v;validate()},{type:"number",min:0,max:100,disabled:inactivity.mode!=="dim"})
    ]),
    settingsGroup("Horario nocturno","Ajustes especiales que se aplican según la hora del panel.",[
      inputField("Activar horario",night.enabled?"yes":"no",v=>{night.enabled=v==="yes";renderSettings();renderPreview();validate()},{choices:yesNoChoices,event:"change"}),
      inputField("Desde",night.start,v=>{night.start=v;validate()},{type:"time",disabled:!night.enabled}),
      inputField("Hasta",night.end,v=>{night.end=v;validate()},{type:"time",disabled:!night.enabled}),
      inputField("Brillo nocturno",night.brightness,v=>{night.brightness=v;validate()},{type:"number",min:0,max:100,disabled:!night.enabled}),
      inputField("Al quedar inactiva de noche",night.mode,v=>{night.mode=v;validate()},{choices:idleModeChoices,event:"change",disabled:!night.enabled})
    ]),
    settingsGroup("Sonidos","Volumen y clases de avisos del parlante integrado.",[
      inputField("Sonidos de interfaz",sound.enabled?"yes":"no",v=>{sound.enabled=v==="yes";renderSettings();validate()},{choices:yesNoChoices,event:"change"}),
      inputField("Al tocar controles",sound.touch?"yes":"no",v=>{sound.touch=v==="yes";validate()},{choices:yesNoChoices,event:"change",disabled:!sound.enabled}),
      inputField("Volumen de toques",sound.touch_volume,v=>{sound.touch_volume=v;validate()},{type:"number",min:0,max:10,disabled:!sound.enabled||!sound.touch}),
      inputField("Al cambiar página",sound.navigation?"yes":"no",v=>{sound.navigation=v==="yes";validate()},{choices:yesNoChoices,event:"change",disabled:!sound.enabled}),
      inputField("Volumen de navegación",sound.navigation_volume,v=>{sound.navigation_volume=v;validate()},{type:"number",min:0,max:10,disabled:!sound.enabled||!sound.navigation}),
      inputField("Notificaciones de Home Assistant",sound.notifications?"yes":"no",v=>{sound.notifications=v==="yes";renderSettings();validate()},{choices:yesNoChoices,event:"change"}),
      inputField("Volumen de notificaciones",sound.notification_volume,v=>{sound.notification_volume=v;sound.volume=v;validate()},{type:"number",min:0,max:10,disabled:!sound.notifications}),
      inputField("Silenciar todo en horario nocturno",sound.mute_at_night?"yes":"no",v=>{sound.mute_at_night=v==="yes";validate()},{choices:yesNoChoices,event:"change"})
    ])
  );
  const calibration=document.createElement("div");calibration.className="ldr-calibration";calibration.innerHTML='<div class="ldr-live"><strong id="ldrReading">LDR: esperando lectura…</strong><span id="brightnessReading">Brillo aplicado: esperando…</span><span id="runtimeMode">Estado: esperando…</span></div><div><button class="text-button" data-cal="dark">Usar actual como oscuridad</button><button class="text-button" data-cal="bright">Usar actual como mucha luz</button></div>';
  const displayGrid=displaySection.querySelector(".settings-grid");displayGrid.append(calibration);calibration.querySelectorAll("button").forEach(button=>button.onclick=async()=>{await loadLdrStatus();if(!Number.isFinite(state.ldrVoltage))return showToast("Todavía no hay una lectura del LDR.",true);const value=Math.round(state.ldrVoltage*100)/100;if(button.dataset.cal==="dark"){display.ldr_dark_voltage=value;ldrDarkField.querySelector("input").value=value}else{display.ldr_bright_voltage=value;ldrBrightField.querySelector("input").value=value}validate();showToast(`Valor ${value.toFixed(2)} V copiado. Falta Guardar y aplicar.`)});
  const test=document.createElement("button");test.className="button secondary settings-test";test.textContent="Probar notificación";test.disabled=!sound.notifications||sound.notification_volume===0;test.onclick=async()=>{try{await api("/api/test-sound",{method:"POST",body:JSON.stringify({volume:Number(sound.notification_volume)})});showToast(`Notificación de prueba enviada al volumen ${sound.notification_volume}.`)}catch(error){showToast(error.message,true)}};pageForm.lastElementChild.querySelector(".settings-grid").append(test);
  const touchSection=settingsGroup("Pantalla táctil","Calibración individual para compensar diferencias entre paneles resistivos.",[]);const touchBox=document.createElement("div");touchBox.className="touch-calibration";touchBox.innerHTML='<div><strong id="touchCalibrationStatus"></strong><span>Tocá los cuatro puntos que aparecerán en la pantalla.</span></div><button class="button secondary">Iniciar calibración</button>';touchSection.querySelector(".settings-grid").append(touchBox);pageForm.append(touchSection);const touchStatus=touchBox.querySelector("strong"),touchButton=touchBox.querySelector("button");touchStatus.textContent=`Actual: X ${touchscreen.x_min}–${touchscreen.x_max} · Y ${touchscreen.y_min}–${touchscreen.y_max}`;touchButton.onclick=async()=>{try{await loadLdrStatus();state.touchCalibrationBaseline=state.deviceTouchCalibration?.completed_at??null;state.touchCalibrationWaiting=true;touchButton.disabled=true;touchStatus.textContent="Calibración en curso… mirá la pantalla";await api("/api/touch-calibration/start",{method:"POST",body:"{}"});showToast("Seguí los cuatro puntos que aparecen en la pantalla.")}catch(error){state.touchCalibrationWaiting=false;touchButton.disabled=false;showToast(error.message,true)}};
  startLdrPolling();
}
function stopLdrPolling(){if(ldrPollingTimer!==null){clearInterval(ldrPollingTimer);ldrPollingTimer=null}}
function startLdrPolling(){stopLdrPolling();loadLdrStatus();ldrPollingTimer=setInterval(()=>{if(state.editingSettings&&document.visibilityState==="visible")loadLdrStatus()},1000)}
async function loadLdrStatus(){try{const status=await api("/api/device-status");state.ldrVoltage=Number.isFinite(status.ldr_voltage)?status.ldr_voltage:null;state.deviceBrightness=Number.isFinite(status.brightness_percent)?status.brightness_percent:null;state.deviceMode=status.mode||null;state.deviceNight=status.night===true;state.deviceTouchCalibration=status.touch_calibration||null;const label=$("#ldrReading"),brightness=$("#brightnessReading"),mode=$("#runtimeMode");if(label)label.textContent=state.ldrVoltage===null?"LDR: esperando lectura del panel…":`LDR actual: ${state.ldrVoltage.toFixed(3)} V`;if(brightness)brightness.textContent=state.deviceBrightness===null?"Brillo aplicado: esperando…":`Brillo aplicado: ${Math.round(state.deviceBrightness)} %`;if(mode){const names={normal:"Normal",night:"Horario nocturno",clock_weather:"Protector reloj y clima",screen_off:"Pantalla apagada",dim:"Brillo tenue",idle:"En reposo"};mode.textContent=state.deviceMode===null?"Estado: esperando…":`Estado: ${names[state.deviceMode]||state.deviceMode}${state.deviceNight&&state.deviceMode!=="night"?" (noche)":""}`};const touchStatus=$("#touchCalibrationStatus"),touchButton=touchStatus?.closest(".touch-calibration")?.querySelector("button"),result=state.deviceTouchCalibration;if(state.touchCalibrationWaiting&&result&&result.completed_at!==state.touchCalibrationBaseline){state.touchCalibrationWaiting=false;if(result.success){Object.assign(state.ui.settings.touchscreen,{x_min:result.x_min,x_max:result.x_max,y_min:result.y_min,y_max:result.y_max});if(touchStatus)touchStatus.textContent=`Nueva: X ${result.x_min}–${result.x_max} · Y ${result.y_min}–${result.y_max}`;showToast("Calibración completada. Guardá y aplicá para conservarla.")}else{if(touchStatus)touchStatus.textContent="La calibración no se completó.";showToast("La calibración fue cancelada; se conserva la anterior.",true)}if(touchButton)touchButton.disabled=false;validate()}}catch(error){state.ldrVoltage=null;const label=$("#ldrReading");if(label)label.textContent="LDR: sin datos"}return state.ldrVoltage}
// Each field updates state.ui as it changes. Do not read controls by their
// position here: adding a new settings section would silently corrupt values.
function syncSettingsForm(){if(!state.editingSettings)return;ensureSettings();state.ui.screensaver_timeout=state.ui.settings.inactivity.timeout;state.ui.settings.sound.volume=state.ui.settings.sound.notification_volume}
function entityChoices(current,control,page){
  const allowed=page.template==="climate"?["climate"]:page.template==="cover"?["cover"]:page.template==="media"?["media_player"]:page.template==="clock_weather"?["weather","sensor"]:page.template==="sensor_grid"?["sensor","binary_sensor"]:["light","switch","scene","script","input_boolean","button","fan"];
  const choices=[{value:"",label:"Sin asociar"}],seen=new Set();state.entities.filter(e=>allowed.includes(e.domain)).forEach(e=>{seen.add(e.entity_id);choices.push({value:e.entity_id,label:`${e.name}  ·  ${e.entity_id}`})});if(current&&!seen.has(current))choices.splice(1,0,{value:current,label:`${current} (actual)`});return choices;
}
function configureMappingForEntity(control,mapping,entityId,page,preserveLabels=false){
  mapping.entity_id=entityId;
  if(!entityId){delete mapping.domain;return}
  const domain=entityId.split(".")[0];mapping.domain=domain;
  const entity=state.entities.find(item=>item.entity_id===entityId);
  if(page.template==="media"){
    const defaults=defaultMapping(control);Object.assign(mapping,defaults,{entity_id:entityId,domain});
    return;
  }
  if(page.template==="sensor_grid"){
    delete mapping.attribute;mapping.value_only=true;
    if(domain==="binary_sensor"){
      delete mapping.decimals;control.unit="";
      mapping.state_active=true;
      const labels={motion:["Mov.","Libre"],occupancy:["Ocupado","Libre"],presence:["Presente","Ausente"],door:["Abierta","Cerrada"],window:["Abierta","Cerrada"],opening:["Abierto","Cerrado"],garage_door:["Abierto","Cerrado"],moisture:["Húmedo","Seco"],smoke:["Humo","Normal"],gas:["Gas","Normal"],problem:["Problema","Normal"],safety:["Riesgo","Seguro"],connectivity:["Conectado","Sin red"],battery:["Baja","Batería OK"],light:["Luz","Oscuro"],sound:["Sonido","Silencio"],vibration:["Vibra","Quieto"],moving:["Moviendo","Detenido"],running:["En marcha","Detenido"],tamper:["Alerta","Normal"],update:["Pendiente","Al día"]};
      const icons={motion:["mdi:motion-sensor","mdi:motion-sensor-off"],occupancy:["mdi:eye","mdi:eye-off"],presence:["mdi:eye","mdi:eye-off"],door:["mdi:door-open","mdi:door-closed"],window:["mdi:window-open","mdi:window-closed"],opening:["mdi:lock-open","mdi:lock"],garage_door:["mdi:garage-open","mdi:garage"],moisture:["mdi:water-percent","mdi:check-circle"],smoke:["mdi:alert","mdi:check-circle"],gas:["mdi:alert","mdi:check-circle"],problem:["mdi:alert","mdi:check-circle"],safety:["mdi:alert","mdi:check-circle"],connectivity:["mdi:wifi","mdi:wifi-off"],battery:["mdi:battery-alert","mdi:battery"],light:["mdi:lightbulb","mdi:lightbulb-off"],sound:["mdi:speaker","mdi:speaker"],vibration:["mdi:motion-sensor","mdi:motion-sensor-off"],moving:["mdi:play","mdi:stop"],running:["mdi:play","mdi:stop"],tamper:["mdi:alert","mdi:check-circle"],update:["mdi:alert","mdi:check-circle"]};
      const pair=labels[entity?.device_class]||["Activo","Inactivo"];
      const iconPair=icons[entity?.device_class]||["mdi:toggle-switch","mdi:toggle-switch-off"];
      if(!preserveLabels||!mapping.value_map)mapping.value_map={on:pair[0],off:pair[1]};
      if(!preserveLabels||!("icon_on" in control)){control.icon_on=iconPair[0];control.icon_off=iconPair[1]}
    }else{
      delete mapping.value_map;
      if(entity?.unit&&!control.unit)control.unit=entity.unit;
      if(entity&&Number.isFinite(Number(entity.state))&&mapping.decimals===undefined){const decimal=String(entity.state).split(".")[1];mapping.decimals=decimal?Math.min(decimal.length,2):0}
    }
  }
  if(page.template!=="button_grid"||control.type!=="button")return;
  mapping.allow_control=true;delete mapping.service;delete mapping.publish_state;
  const behavior={scene:["activate","turn_on"],script:["run","turn_on"],button:["press","press"]}[domain]||["toggle","toggle"];
  control.action=behavior[0];mapping.action=behavior[0];
  if(behavior[1]!==behavior[0])mapping.service=behavior[1];
  if(["scene","script","button"].includes(domain))mapping.publish_state=false;
}
function normalizeEntityMappings(){
  state.ui.pages.filter(page=>page.template==="sensor_grid").forEach(page=>page.controls.forEach(control=>{const mapping=state.backendMap.controls[control.id];if(mapping?.entity_id&&mapping.entity_id.startsWith("binary_sensor."))configureMappingForEntity(control,mapping,mapping.entity_id,page,true)}));
}
function migrateMappingId(oldId,newId){if(oldId===newId)return;const mapping=state.backendMap.controls[oldId]||{};delete state.backendMap.controls[oldId];state.backendMap.controls[newId]=mapping}
function renderControls(){const page=state.ui.pages[state.selectedPage];controlList.replaceChildren();page.controls.forEach((control,index)=>{const mapping=state.backendMap.controls[control.id]||=(defaultMapping(control));const card=document.createElement("div");card.className=`control-card${state.collapsed.has(control.id)?" collapsed":""}`;const summary=document.createElement("div");summary.className="control-summary";summary.innerHTML='<i class="color-dot"></i><strong></strong><span></span>';const dot=summary.querySelector("i"),summaryTitle=summary.querySelector("strong");dot.style.background=control.color;summaryTitle.textContent=control.caption;summary.querySelector("span").textContent=control.role||control.type;summary.onclick=()=>{state.collapsed.has(control.id)?state.collapsed.delete(control.id):state.collapsed.add(control.id);renderControls()};const fields=document.createElement("div");fields.className="control-fields";const choices=entityChoices(mapping.entity_id,control,page),compatibleCount=Math.max(0,choices.length-1);fields.append(inputField("Texto visible",control.caption,v=>{control.caption=v;summaryTitle.textContent=v;renderPreview();validate()}),inputField(control.type==="button"?"Color cuando está activo":"Color",control.color,v=>{control.color=v.toUpperCase();dot.style.background=control.color;renderPreview();validate()},{type:"color"}),inputField("ID interno",control.id,v=>{const oldId=control.id;control.id=slug(v);migrateMappingId(oldId,control.id);validate()},{event:"change"}),inputField(`Entidad de Home Assistant · ${compatibleCount} compatibles`,mapping.entity_id||"",v=>{configureMappingForEntity(control,mapping,v,page);renderControls();renderPreview();validate()},{choices,searchable:true,event:"change",wide:true}));if(control.type==="value"&&mapping.domain==="binary_sensor"){mapping.value_map||=( {on:"Activo",off:"Inactivo"} );fields.append(inputField("Texto o símbolo activo (on)",mapping.value_map.on||"",v=>{mapping.value_map.on=v;renderPreview();validate()},{placeholder:"Ej.: Mov., Abierta, ●"}),inputField("Texto o símbolo inactivo (off)",mapping.value_map.off||"",v=>{mapping.value_map.off=v;renderPreview();validate()},{placeholder:"Ej.: Libre, Cerrada, ○"}),inputField("Ícono activo (on)",control.icon_on||"",v=>{control.icon_on=v;renderPreview();validate()},{choices:iconChoices(control.icon_on),searchable:true}),inputField("Ícono inactivo (off)",control.icon_off||"",v=>{control.icon_off=v;renderPreview();validate()},{choices:iconChoices(control.icon_off),searchable:true}))}else if(control.type==="value")fields.append(inputField("Dato a mostrar",mapping.attribute||"",v=>{if(v){mapping.attribute=v;delete mapping.value_only}else{delete mapping.attribute;mapping.value_only=true}},{choices:attributeChoices(mapping.entity_id,mapping.attribute),event:"change"}),inputField("Decimales",mapping.decimals??"",v=>{if(v===""||Number.isNaN(v))delete mapping.decimals;else mapping.decimals=Number(v)},{type:"number"}),inputField("Unidad",control.unit||"",v=>{control.unit=v;renderPreview()},{placeholder:"°C, %, W…"}),inputField("Ícono",control.icon||"",v=>{control.icon=v;renderPreview();validate()},{choices:iconChoices(control.icon),searchable:true}));else{const readOnly=control.role==="power"&&mapping.allow_control!==true;fields.append(inputField(readOnly?"Uso":"Qué debe hacer",readOnly?"Solo muestra el estado":(control.action||mapping.action||"toggle"),v=>{setControlAction(control,mapping,v);validate()},readOnly?{disabled:true}:{choices:actionChoices(mapping,control),event:"change"}),inputField("Ícono",control.icon||"",v=>{control.icon=v;renderPreview();validate()},{choices:iconChoices(control.icon),searchable:true}))}if(state.catalog[page.template].controls.kind==="variable"&&page.controls.length>1){const remove=document.createElement("button");remove.className="text-button danger";remove.textContent="Quitar control";remove.onclick=()=>{delete state.backendMap.controls[control.id];page.controls.splice(index,1);renderAll()};fields.append(remove)}card.append(summary,fields);controlList.append(card)})}

function renderReminderComposer(){
  const draft=state.reminderDraft;
  $("#editorTitle").textContent="Enviar recordatorio";
  pageForm.classList.add("settings-form");pageForm.replaceChildren();
  const section=settingsGroup("Aviso en pantalla","Despierta la CYD y permanece visible hasta pulsar ACEPTAR.",[
    inputField("Identificador",draft.reminder_id,v=>draft.reminder_id=slug(v),{placeholder:"medicacion_noche"}),
    inputField("Título",draft.title,v=>{draft.title=v;renderReminderPreview()},{wide:true}),
    inputField("Mensaje",draft.message,v=>{draft.message=v;renderReminderPreview()},{placeholder:"Escribí el recordatorio…",wide:true}),
    inputField("Prioridad",draft.level,v=>{draft.level=v;renderReminderPreview()},{choices:[{value:"info",label:"Información · azul"},{value:"reminder",label:"Recordatorio · verde"},{value:"warning",label:"Advertencia · amarillo"},{value:"urgent",label:"Urgente · rojo"}],event:"change"}),
    inputField("Sonido",draft.sound_mode,v=>{draft.sound_mode=v;renderReminderComposer();renderReminderPreview()},{choices:[{value:"silent",label:"Sin sonido"},{value:"once",label:"Un aviso"},{value:"alarm",label:"Alarma repetida"}],event:"change"}),
    ...(draft.sound_mode==="alarm"?[
      inputField("Duración máxima",draft.alarm_duration,v=>draft.alarm_duration=v,{choices:[{value:30,label:"30 segundos"},{value:60,label:"1 minuto"},{value:120,label:"2 minutos"}],event:"change"}),
      inputField("Botón Aplazar",draft.snooze_minutes,v=>{draft.snooze_minutes=v;renderReminderPreview()},{choices:[{value:0,label:"Sin Aplazar"},{value:5,label:"5 minutos"},{value:10,label:"10 minutos"},{value:15,label:"15 minutos"}],event:"change"})
    ]:[])
  ]);
  const actions=document.createElement("div");actions.className="inline-actions reminder-actions";
  const send=document.createElement("button");send.className="button primary";send.textContent="Enviar ahora";
  send.onclick=async()=>{if(!draft.message.trim())return showToast("Escribí un mensaje para el recordatorio.",true);send.disabled=true;try{await api("/api/reminder/send",{method:"POST",body:JSON.stringify(draft)});showToast("Recordatorio enviado a la pantalla.")}catch(error){showToast(error.message,true)}finally{send.disabled=false}};
  const dismiss=document.createElement("button");dismiss.className="button secondary";dismiss.textContent="Retirar aviso";
  dismiss.onclick=async()=>{try{await api("/api/reminder/dismiss",{method:"POST",body:JSON.stringify({reminder_id:draft.reminder_id})});showToast("Orden para retirar el aviso enviada.")}catch(error){showToast(error.message,true)}};
  actions.append(send,dismiss);section.querySelector(".settings-grid").append(actions);pageForm.append(section);

  if(!state.reminderScheduleAt)state.reminderScheduleAt=defaultReminderSchedule();
  const scheduleSection=settingsGroup("Programar para más tarde","La agenda queda guardada en Home Assistant y sobrevive a reinicios.",[
    inputField(state.reminderRepeat==="once"?"Fecha y hora":"Primera fecha y hora",state.reminderScheduleAt,v=>state.reminderScheduleAt=v,{type:"datetime-local",wide:true}),
    inputField("Repetir",state.reminderRepeat,v=>{state.reminderRepeat=v;if(v!=="custom")state.reminderWeekdays=[];renderReminderComposer()},{choices:[{value:"once",label:"Una sola vez"},{value:"daily",label:"Todos los días"},{value:"weekdays",label:"Lunes a viernes"},{value:"weekly",label:"Todas las semanas"},{value:"custom",label:"Elegir días"}],event:"change",wide:true})
  ]);
  if(state.reminderRepeat==="custom")scheduleSection.querySelector(".settings-grid").append(renderWeekdayPicker());
  const scheduleActions=document.createElement("div");scheduleActions.className="inline-actions reminder-actions";
  const schedule=document.createElement("button");schedule.className="button primary";schedule.textContent="Programar recordatorio";
  schedule.onclick=async()=>{if(!draft.message.trim())return showToast("Escribí un mensaje para el recordatorio.",true);const date=new Date(state.reminderScheduleAt);if(!Number.isFinite(date.getTime()))return showToast("Elegí una fecha y hora válidas.",true);if(state.reminderRepeat==="custom"&&!state.reminderWeekdays.length)return showToast("Elegí al menos un día de la semana.",true);schedule.disabled=true;try{await api("/api/reminder/schedule",{method:"POST",body:JSON.stringify({...draft,scheduled_at:date.toISOString(),repeat:state.reminderRepeat,weekdays:state.reminderWeekdays})});state.reminderScheduleAt=defaultReminderSchedule();await loadScheduledReminders();showToast(state.reminderRepeat==="once"?"Recordatorio programado.":"Recordatorio repetitivo programado.");renderReminderComposer()}catch(error){showToast(error.message,true)}finally{schedule.disabled=false}};
  scheduleActions.append(schedule);scheduleSection.querySelector(".settings-grid").append(scheduleActions);pageForm.append(scheduleSection);
  renderReminderAgenda();
}

function defaultReminderSchedule(){const date=new Date(Date.now()+10*60000);date.setSeconds(0,0);const local=new Date(date.getTime()-date.getTimezoneOffset()*60000);return local.toISOString().slice(0,16)}
function renderWeekdayPicker(){const field=document.createElement("div");field.className="field wide weekday-field";field.innerHTML="<span>Días de la semana</span>";const picker=document.createElement("div");picker.className="weekday-picker";["L","M","X","J","V","S","D"].forEach((label,index)=>{const button=document.createElement("button");button.type="button";button.className=`weekday-button${state.reminderWeekdays.includes(index)?" active":""}`;button.textContent=label;button.setAttribute("aria-label",["Lunes","Martes","Miércoles","Jueves","Viernes","Sábado","Domingo"][index]);button.onclick=()=>{state.reminderWeekdays=state.reminderWeekdays.includes(index)?state.reminderWeekdays.filter(day=>day!==index):[...state.reminderWeekdays,index].sort();renderReminderComposer()};picker.append(button)});field.append(picker);return field}
function reminderRepeatLabel(item){const repeat=item.repeat||"once";if(repeat==="daily")return"Todos los días";if(repeat==="weekdays")return"Lunes a viernes";if(repeat==="weekly")return"Semanal";if(repeat==="custom"){const names=["Lun","Mar","Mié","Jue","Vie","Sáb","Dom"];return(item.weekdays||[]).map(day=>names[day]).join(", ")||"Días elegidos"}return"Una vez"}
async function loadScheduledReminders(){try{const result=await api("/api/reminder/schedules");state.scheduledReminders=result.items||[]}catch(error){state.scheduledReminders=[];showToast(error.message,true)}}
function formatReminderDate(value){const date=new Date(value);return Number.isFinite(date.getTime())?new Intl.DateTimeFormat("es-UY",{dateStyle:"short",timeStyle:"short"}).format(date):value}
function renderReminderAgenda(){
  const section=document.createElement("section");section.className="settings-section reminder-agenda";
  const heading=document.createElement("div");heading.className="settings-section-heading";heading.innerHTML="<h3>Próximos recordatorios</h3><p></p>";heading.querySelector("p").textContent=state.scheduledReminders.length?`${state.scheduledReminders.length} pendiente${state.scheduledReminders.length===1?"":"s"}.`:"No hay recordatorios programados.";section.append(heading);
  const list=document.createElement("div");list.className="reminder-agenda-list";
  state.scheduledReminders.forEach(item=>{const card=document.createElement("div");card.className="reminder-agenda-item";const content=document.createElement("div");content.innerHTML="<strong></strong><span></span><small></small>";content.querySelector("strong").textContent=item.payload?.title||"Recordatorio";content.querySelector("span").textContent=item.payload?.message||"";content.querySelector("small").textContent=`${formatReminderDate(item.scheduled_at)} · ${reminderRepeatLabel(item)}${item.status==="retrying"?" · esperando conexión":""}`;const cancel=document.createElement("button");cancel.className="text-button danger";cancel.textContent="Cancelar";cancel.onclick=async()=>{cancel.disabled=true;try{await api("/api/reminder/schedule/cancel",{method:"POST",body:JSON.stringify({schedule_id:item.id})});await loadScheduledReminders();renderReminderComposer();showToast("Recordatorio cancelado.")}catch(error){showToast(error.message,true)}finally{cancel.disabled=false}};card.append(content,cancel);list.append(card)});
  section.append(list);pageForm.append(section);
}

function renderReminderPreview(){
  const draft=state.reminderDraft,screen=document.createElement("div");
  screen.className=`screen reminder-preview reminder-${draft.level}`;
  screen.innerHTML='<div class="reminder-preview-card"><h3></h3><p></p><div class="reminder-preview-actions"><button class="snooze hidden">APLAZAR</button><button>ACEPTAR</button></div></div>';
  screen.querySelector("h3").textContent=draft.title||"Recordatorio";
  screen.querySelector("p").textContent=draft.message||"Tu mensaje aparecerá aquí.";
  screen.querySelector(".snooze").classList.toggle("hidden",draft.sound_mode!=="alarm"||Number(draft.snooze_minutes)===0);
  preview.replaceChildren(screen);
}
const baseRenderControls=renderControls;
renderControls=function renderControlsWithMediaFallbacks(){
  baseRenderControls();
  const page=state.ui.pages[state.selectedPage];if(page.template!=="media")return;
  const fallbackChoices=[{value:"",label:"Sin fuente alternativa"},...state.entities.filter(entity=>["sensor","text","input_text"].includes(entity.domain)).map(entity=>({value:entity.entity_id,label:`${entity.name} · ${entity.entity_id}`}))];
  page.controls.forEach((control,index)=>{if(!["title","artist","station"].includes(control.role))return;const mapping=state.backendMap.controls[control.id],fields=controlList.children[index]?.querySelector(".control-fields");if(!fields)return;fields.append(inputField("Fuente alternativa (opcional)",mapping.fallback_entity_id||"",value=>{if(value){mapping.fallback_entity_id=value;mapping.fallback_for_entity_id=mapping.entity_id}else{delete mapping.fallback_entity_id;delete mapping.fallback_for_entity_id}validate()},{choices:fallbackChoices,searchable:true,wide:true}))});
};

function renderSettingsPreview(){ensureSettings();const {display,appearance,inactivity,night,sound}=state.ui.settings,screen=document.createElement("div");screen.className=`screen settings-preview ${appearance.mode} accent-${appearance.accent}`;screen.style.opacity=Math.max(.18,display.auto_brightness?1:display.brightness/100);screen.innerHTML='<div class="settings-preview-icon">⚙</div><h3>Configuración</h3><div class="settings-preview-lines"><span></span><span></span><span></span><span></span></div>';const lines=screen.querySelectorAll("span");lines[0].textContent=`Brillo: ${display.auto_brightness?"Automático":display.brightness+" %"}`;lines[1].textContent=`Reposo: ${inactivity.timeout===0?"Desactivado":inactivity.timeout+" s"}`;lines[2].textContent=`Noche: ${night.enabled?night.start+" – "+night.end:"Desactivada"}`;lines[3].textContent=`Sonido: ${sound.enabled?`T${sound.touch_volume} N${sound.navigation_volume} A${sound.notification_volume}${sound.mute_at_night?" · noche off":""}`:"Apagado"}`;preview.replaceChildren(screen)}
function renderPreview(){if(state.editingSettings)return renderSettingsPreview();const page=state.ui.pages[state.selectedPage],screen=document.createElement("div");screen.className="screen";if(page.template==="clock_weather")screen.innerHTML='<div class="clock-face"><div class="clock-time">10:42</div><div class="clock-date">Miercoles 29 de julio</div><div class="clock-condition">Despejado</div><div class="clock-temperature">21.5 C</div><div class="clock-humidity">Humedad 58 %</div><small>Toca para volver</small></div>';else{const title=document.createElement("div");title.className="screen-title";title.textContent=page.title||"Sin título";const grid=document.createElement("div");grid.className="preview-grid";const count=page.controls.length;if(page.template==="button_grid")grid.style.gridTemplateColumns=count===2?"1fr 1fr":count===4?"1fr 1fr":"1fr 1fr 1fr";else if(page.template==="sensor_grid")grid.style.gridTemplateColumns="1fr 1fr";else grid.style.gridTemplateColumns="1fr 1fr 1fr";page.controls.forEach(control=>{const mapping=state.backendMap.controls[control.id]||{};const item=document.createElement("div");item.className=`preview-control${control.type==="value"?" preview-value":""}`;item.style.borderColor=control.color;item.style.background=`${control.color}22`;item.innerHTML=control.type==="value"?'<span></span><div class="preview-reading"><i class="preview-mdi"></i><b></b></div>':'<i class="preview-mdi"></i><span></span>';item.querySelector("span").textContent=control.caption;const iconName=mapping.domain==="binary_sensor"?(control.icon_off||control.icon):(control.icon||"");const icon=item.querySelector(".preview-mdi");icon.textContent=iconGlyph(iconName);icon.classList.toggle("hidden",!icon.textContent);if(control.type==="value")item.querySelector("b").textContent=mapping.domain==="binary_sensor"?(mapping.value_map?.off||"Inactivo"):`--${control.unit||""}`;grid.append(item)});const nav=document.createElement("div");nav.className="preview-nav";nav.innerHTML=`<span>‹</span><small>${state.selectedPage+1} / ${state.ui.pages.length}</small><span>›</span>`;screen.append(title,grid,nav)}preview.replaceChildren(screen)}
async function validate(){try{const result=await api("/api/validate",{method:"POST",body:JSON.stringify({ui:state.ui,backend_map:state.backendMap})});validationBox.className=`validation-box ${result.valid?"valid":"invalid"}`;validationBox.innerHTML=result.valid?"✓ Configuración lista para guardar.":result.errors.slice(0,5).map(e=>`• ${e}`).join("<br>");saveButton.disabled=!result.valid;return result.valid}catch(error){validationBox.className="validation-box invalid";validationBox.textContent=error.message;saveButton.disabled=true;return false}}
function renderAll(){
  state.selectedPage=Math.max(0,Math.min(state.selectedPage,state.ui.pages.length-1));ensureSettings();renderPages();
  const auxiliary=state.editingSettings||state.editingReminder;
  $("#duplicateButton").classList.toggle("hidden",auxiliary);$("#deleteButton").classList.toggle("hidden",auxiliary);
  $("#controlsHeading").classList.toggle("hidden",auxiliary);controlList.classList.toggle("hidden",auxiliary);
  saveButton.classList.toggle("hidden",state.editingReminder);
  if(state.editingReminder){stopLdrPolling();renderReminderComposer()}
  else if(state.editingSettings){renderSettings()}
  else{stopLdrPolling();pageForm.classList.remove("settings-form");renderPageForm();renderControls()}
  renderPreview();validate()
}
async function loadEntities(){$("#entityCount").textContent="Consultando Home Assistant…";try{const result=await api("/api/entities");state.entities=result.entities;normalizeEntityMappings();$("#entityCount").textContent=`${state.entities.length} entidades totales`;renderControls();renderPreview();validate()}catch(error){$("#entityCount").textContent="Home Assistant no disponible";showToast(error.message,true)}}
async function initialize(){try{const[catalog,icons,project]=await Promise.all([api("/api/catalog"),api("/api/icons"),api("/api/project")]);state.catalog=catalog;state.icons=icons.icons;state.ui=project.ui;state.backendMap=project.backend_map;ensureSettings();$("#connectionState").textContent="Proyecto cargado";$("#connectionState").className="status ok";renderAll();loadEntities()}catch(error){$("#connectionState").textContent="Error de carga";$("#connectionState").className="status bad";showToast(error.message,true)}}

// Searchable choices use real touch buttons instead of a multi-row <select>.
// Android/iOS handle those reliably, while a size=5 select is inconsistent.
function inputField(label,value,onChange,options={}){
  const field=document.createElement("div");
  field.className=`field${options.wide?" wide":""}`;
  const caption=document.createElement("label");
  caption.textContent=label;
  let input,extra=null;
  if(options.choices&&options.searchable){
    input=document.createElement("input");
    input.type="search";
    input.value=value??"";
    input.placeholder=options.placeholder||"Escribí para buscar…";
    input.autocomplete="off";
    const results=document.createElement("div");
    results.className="search-results search-result-buttons";
    const renderResults=()=>{
      const query=input.value.trim().toLocaleLowerCase();
      results.replaceChildren();
      if(!query){
        const hint=document.createElement("div");
        hint.className="search-hint";
        hint.textContent=value?"Escribí para cambiar la selección.":"Escribí al menos una parte del nombre o ID.";
        results.append(hint);
        return;
      }
      const matches=options.choices.filter(choice=>`${choice.label} ${choice.value}`.toLocaleLowerCase().includes(query));
      if(!matches.length){
        const empty=document.createElement("div");
        empty.className="search-hint";
        empty.textContent="Sin coincidencias";
        results.append(empty);
        return;
      }
      matches.slice(0,24).forEach(choice=>{
        const result=document.createElement("button");
        result.type="button";
        result.className="search-result";
        result.textContent=choice.label;
        result.onclick=()=>{input.value=choice.value;onChange(choice.value)};
        results.append(result);
      });
    };
    input.addEventListener("input",renderResults);
    input.addEventListener("change",()=>{const exact=options.choices.find(choice=>choice.value===input.value);if(exact||input.value==="")onChange(input.value)});
    renderResults();
    extra=results;
  }else if(options.choices){
    input=document.createElement("select");
    options.choices.forEach(o=>{const option=document.createElement("option");option.value=o.value;option.textContent=o.label;option.selected=String(o.value)===String(value);input.append(option)});
  }else{
    input=document.createElement("input");
    input.type=options.type||"text";
    input.value=value??"";
    if(options.placeholder)input.placeholder=options.placeholder;
    if(options.min!==undefined)input.min=options.min;
    if(options.max!==undefined)input.max=options.max;
    if(options.step!==undefined)input.step=options.step;
  }
  input.disabled=Boolean(options.disabled);
  if(!input.disabled&&!options.searchable){
    const eventName=options.event||"input";
    const handler=()=>onChange(options.type==="number"&&input.value!==""?Number(input.value):input.value);
    input.addEventListener(eventName,handler);
    if(eventName!=="change")input.addEventListener("change",handler);
  }
  field.append(caption,input);
  if(extra)field.append(extra);
  return field;
}

$("#addPageButton").onclick=()=>{if(state.ui.pages.length>=8)return showToast("El firmware admite un máximo de 8 páginas.",true);state.ui.pages.push(makePage());state.selectedPage=state.ui.pages.length-1;state.editingSettings=false;state.editingReminder=false;renderAll()};
$("#deviceSettingsButton").onclick=()=>{state.editingSettings=true;state.editingReminder=false;renderAll()};
$("#reminderCenterButton").onclick=async()=>{state.editingSettings=false;state.editingReminder=true;await loadScheduledReminders();renderAll()};
$("#duplicateButton").onclick=()=>{if(state.ui.pages.length>=8)return showToast("El firmware admite un máximo de 8 páginas.",true);const source=state.ui.pages[state.selectedPage],copy=clone(source);copy.title=`${copy.title} copia`;copy.controls.forEach(control=>{const oldId=control.id;control.id=uniqueId(`${control.id}_copia`);state.backendMap.controls[control.id]=clone(state.backendMap.controls[oldId]||defaultMapping(control))});state.ui.pages.splice(state.selectedPage+1,0,copy);state.selectedPage++;renderAll()};
$("#deleteButton").onclick=()=>{if(state.ui.pages.length===1)return showToast("Debe quedar al menos una página.",true);const page=state.ui.pages[state.selectedPage];if(!confirm(`¿Eliminar “${page.title}”?`))return;removeMappings(page);state.ui.pages.splice(state.selectedPage,1);renderAll()};
$("#addControlButton").onclick=()=>{const page=state.ui.pages[state.selectedPage];if(page.controls.length>=4)return;page.controls.push(makeControl(page.template,{type:"value",caption:`Valor ${page.controls.length+1}`},page.controls.length));renderAll()};
saveButton.onclick=async()=>{syncSettingsForm();if(!(await validate()))return;saveButton.disabled=true;saveButton.textContent="Guardando…";try{const expectedUi=clone(state.ui),expectedBackendMap=clone(state.backendMap),result=await api("/api/save",{method:"POST",body:JSON.stringify({ui:expectedUi,backend_map:expectedBackendMap})}),stored=await api("/api/project"),problems=[];if(JSON.stringify(stored.ui)!==JSON.stringify(expectedUi)||JSON.stringify(stored.backend_map)!==JSON.stringify(expectedBackendMap))throw new Error("Home Assistant no devolvió la misma configuración que se intentó guardar.");if(result.reload_error)problems.push(`pantalla: ${result.reload_error}`);if(result.ha_sync_error)problems.push(`Home Assistant: ${result.ha_sync_error}`);showToast(problems.length?`Guardado, pero falló ${problems.join(" · ")}`:`Guardado y verificado. ${result.backup}${result.delivery_note?` · ${result.delivery_note}`:""}`,problems.length>0)}catch(error){showToast(error.message,true)}finally{saveButton.textContent="Guardar en Home Assistant";validate()}};
$("#reloadButton").onclick=async()=>{try{await api("/api/reload",{method:"POST",body:"{}"});showToast("Orden de recarga enviada.")}catch(error){showToast(error.message,true)}};$("#refreshEntitiesButton").onclick=loadEntities;initialize();
