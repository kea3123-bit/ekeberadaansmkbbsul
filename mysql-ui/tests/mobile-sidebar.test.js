const fs=require('node:fs');
const assert=require('node:assert/strict');
const css=fs.readFileSync('mysql-ui/Styles.html','utf8');
const html=fs.readFileSync('mysql-ui/Index.html','utf8');
const marker='/* iPhone / Android: allow the navigation itself to scroll';
const start=css.indexOf(marker);
assert(start>=0,'Missing mobile sidebar scroll override');
const rules=css.slice(start,css.indexOf('</style>',start));
for(const [selector,terms] of [
  ['.sidebar{',['height:100dvh','overflow:hidden','env(safe-area-inset-bottom']],
  ['.sidebar .menu{',['display:flex','flex-direction:column','flex:1 1 auto','min-height:0','overflow-y:auto','-webkit-overflow-scrolling:touch']],
  ['.sidebar .menu-item{',['flex:0 0 auto']],
  ['.sidebar .sidebar-user{',['flex:0 0 auto','grid-template-columns:38px minmax(0,1fr) 44px']],
  ['.sidebar .sidebar-user .icon-btn{',['width:44px','height:44px']]
]){
  const idx=rules.indexOf(selector);
  assert(idx>=0,'Missing '+selector);
  const end=rules.indexOf('}',idx);
  const block=rules.slice(idx,end);
  for(const term of terms)assert(block.includes(term),selector+' missing '+term);
}
const nav=html.indexOf('<nav class="menu">'),navEnd=html.indexOf('</nav>',nav);
const footer=html.indexOf('<div class="sidebar-user">',navEnd);
const sidebarEnd=html.indexOf('</aside>',footer);
assert(nav>0&&navEnd>nav&&footer>navEnd&&sidebarEnd>footer,'Footer must follow scrollable nav inside sidebar');
assert(html.slice(footer,sidebarEnd).includes('aria-label="Keluar"'),'Logout button must be accessible');
assert(html.slice(footer,sidebarEnd).includes('onclick="logout()"'),'Logout handler must be preserved');
console.log('MOBILE_SIDEBAR_SCROLL_SAFE_AREA_AND_LOGOUT_OK');
