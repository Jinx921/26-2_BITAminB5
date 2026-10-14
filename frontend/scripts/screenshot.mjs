/**
 * 화면 스크린샷. 개발 서버(5173, 목업 모드)가 떠 있어야 한다.
 *   node scripts/screenshot.mjs [out-dir] [prefix]
 * 시민·현장은 390px, 관리자·로그인은 1440px.
 */
import { chromium } from 'playwright'
import { mkdirSync } from 'node:fs'
import { join } from 'node:path'

const BASE = process.env.BASE_URL ?? 'http://127.0.0.1:5173'
const OUT = process.argv[2] ?? 'design'
const PREFIX = process.argv[3] ?? ''
mkdirSync(OUT, { recursive: true })
const file = (name) => join(OUT, `${PREFIX}${name}.png`)

// 실제 백엔드로 찍을 때는 환경 변수로 계정을 넘긴다 (예: ADMIN_PASSWORD=... ONLY=maps node scripts/screenshot.mjs design real-)
const ACCOUNTS = {
  admin: [process.env.ADMIN_EMAIL ?? 'admin@example.com', process.env.ADMIN_PASSWORD ?? 'demo-admin-1234'],
  citizen: [process.env.CITIZEN_EMAIL ?? 'citizen@example.com', process.env.CITIZEN_PASSWORD ?? 'demo-citizen-1234'],
  field: [process.env.FIELD_EMAIL ?? 'field@example.com', process.env.FIELD_PASSWORD ?? 'demo-field-1234'],
}
/** ONLY=maps: 관리자 지도 레이어 6장만 (질문 없이, 실제 API 점검용) */
const ONLY = process.env.ONLY ?? ''

async function login(page, role) {
  await page.goto(`${BASE}/login`)
  await page.evaluate(() => sessionStorage.clear())
  await page.goto(`${BASE}/login`)
  await page.fill('input[type=email]', ACCOUNTS[role][0])
  await page.fill('input[type=password]', ACCOUNTS[role][1])
  await page.click('button[type=submit]')
  await page.waitForURL((u) => !u.pathname.startsWith('/login'))
}

const settle = async (page, ms = 1200) => page.waitForTimeout(ms)
/** fullPage 캡처에서 하단 고정 바가 화면 중간에 찍히지 않게 페이지 끝으로 내린다 */
const fullShot = async (page, path) => {
  await page.addStyleTag({ content: '[data-fixed-bar]{position:absolute !important}' })
  await page.screenshot({ path, fullPage: true })
}

const browser = await chromium.launch()
// 한 컨텍스트를 공유해 localStorage(목업 저장소)가 관리자→현장으로 이어지게 한다
const ctx = await browser.newContext({ deviceScaleFactor: 2 })
const MOBILE = { width: 390, height: 844 }
const DESKTOP = { width: 1440, height: 900 }
async function newPage(viewport) {
  const page = await ctx.newPage()
  await page.setViewportSize(viewport)
  return page
}

if (ONLY === 'maps') {
  const page = await newPage(DESKTOP)
  await login(page, 'admin')
  await settle(page, 2500)
  for (const region of ['춘천', '강남']) {
    await page.getByRole('radio', { name: region === '강남' ? '서울 강남구' : '춘천시' }).click()
    await settle(page, 2500)
    for (const [layer, key] of [['유형', 'types'], ['후보', 'candidates'], ['배치', 'sim']]) {
      await page.getByRole('radio', { name: layer, exact: true }).click()
      await settle(page, 2500)
      await page.screenshot({ path: file(`admin-map-${region}-${key}`) })
    }
  }
  await page.close()
  await browser.close()
  console.log(`saved maps to ${OUT}/ (prefix "${PREFIX}")`)
  process.exit(0)
}

// ---- 로그인 (1440)
{
  const page = await newPage(DESKTOP)
  await page.goto(`${BASE}/login`)
  await settle(page, 600)
  await page.screenshot({ path: file('login'), fullPage: true })
  await page.close()
}

// ---- 시민 (390)
{
  const page = await newPage(MOBILE)
  await login(page, 'citizen')
  await settle(page, 800)
  await fullShot(page, file('citizen-home'))
  // 위치: 지도에서 고르기 → 지도 가운데 클릭 (현재 UI / 새 UI 모두 data-testid 로 시도)
  const pickBtn = page.getByRole('button', { name: /지도에서 고르기/ }).first()
  const locTrigger = page.locator('[data-testid=location-trigger]')
  if (await locTrigger.count()) {
    await locTrigger.click()
    await settle(page, 500)
  }
  if (await pickBtn.count()) {
    await pickBtn.click()
    await settle(page, 1200)
    const map = page.locator('.leaflet-container').first()
    const box = await map.boundingBox()
    if (box) await page.mouse.click(box.x + box.width / 2, box.y + box.height / 2)
    await settle(page, 1500)
    const done = page.locator('[data-testid=location-done]')
    if (await done.count()) await done.click()
  }
  await page.fill('input[aria-label=질문]', '어머니 댁 근처에 다니실 만한 곳 있어요?')
  await page.keyboard.press('Enter')
  await page.waitForSelector('[data-fragment=headline]', { timeout: 15000 })
  await settle(page, 2500)
  await fullShot(page, file('citizen-answer'))
  // 큰 글씨 모드
  await page.getByRole('button', { name: /큰 글씨/ }).click()
  await settle(page, 600)
  await fullShot(page, file('citizen-answer-bigtext'))
  await page.getByRole('button', { name: /글씨/ }).click()
  await settle(page, 300)
  await page.goto(`${BASE}/citizen/places`)
  await settle(page, 2500)
  await fullShot(page, file('citizen-places'))
  // PC 보기 (1440)
  await page.setViewportSize(DESKTOP)
  await page.goto(`${BASE}/citizen`)
  await settle(page, 800)
  await page.getByRole('button', { name: /PC 화면/ }).click()
  await settle(page, 2500)
  await fullShot(page, file('citizen-answer-desktop'))
  await page.goto(`${BASE}/citizen/places`)
  await settle(page, 2500)
  await fullShot(page, file('citizen-places-desktop'))
  await page.getByRole('button', { name: /모바일 화면/ }).click()
  await settle(page, 300)
  await page.setViewportSize(MOBILE)
  const help = page.locator('a[href*="/citizen/help/"]').first()
  if (await help.count()) {
    await help.click()
    await settle(page, 800)
    await fullShot(page, file('citizen-help'))
  }
  await page.goto(`${BASE}/citizen/schedule`)
  await settle(page, 600)
  await fullShot(page, file('citizen-schedule'))
  await page.close()
}

// ---- 관리자 (1440)
{
  const page = await newPage(DESKTOP)
  await login(page, 'admin')
  await settle(page, 2500)
  await page.screenshot({ path: file('admin-home') })
  await page.fill('input[aria-label=질문]', '춘천 외곽에 거점 3곳을 둔다면 이동형이랑 경로당 거점 중 뭐가 나아?')
  await page.keyboard.press('Enter')
  await page.waitForSelector('[data-fragment=headline]', { timeout: 15000 })
  await settle(page, 2500)
  await page.screenshot({ path: file('admin-answer') })
  await page.fill('input[aria-label=질문]', '춘천 현장 확인 목록 만들어 줘')
  await page.keyboard.press('Enter')
  await page.waitForSelector('[data-fragment=headline]', { timeout: 15000 })
  await settle(page, 1500)
  const send = page.getByRole('button', { name: /현장 담당자에게 보내기/ }).first()
  if (await send.count()) {
    await send.click()
    await page.waitForURL(/field-list/)
    await settle(page, 2500)
    await page.screenshot({ path: file('admin-field-list') })
  }
  await page.goto(`${BASE}/admin/requests`)
  await settle(page, 2000)
  await page.screenshot({ path: file('admin-requests') })
  // 지도 레이어 3종 × 지역 2
  await page.goto(`${BASE}/admin`)
  await settle(page, 2000)
  for (const region of ['춘천', '강남']) {
    await page.getByRole('radio', { name: region === '강남' ? '서울 강남구' : '춘천시' }).click()
    await settle(page, 2000)
    for (const [layer, key] of [['유형', 'types'], ['후보', 'candidates'], ['배치', 'sim']]) {
      await page.getByRole('radio', { name: layer, exact: true }).click()
      await settle(page, 2000)
      await page.screenshot({ path: file(`admin-map-${region}-${key}`) })
    }
  }
  // 응답과 함께: 후보 레이어 응답(주민 안내문) / 배치 레이어 응답(이동형 배치, 거점 마커)
  await page.getByRole('radio', { name: '춘천시' }).click()
  await settle(page, 1500)
  await page.fill('input[aria-label=질문]', '춘천 외곽 이동형 건강상담을 알리는 주민 안내문 만들어 줘')
  await page.keyboard.press('Enter')
  await page.waitForSelector('[data-fragment=headline]', { timeout: 15000 })
  await settle(page, 2500)
  await page.screenshot({ path: file('admin-map-춘천-candidates-answer') })
  await page.fill('input[aria-label=질문]', '춘천 외곽에 이동형 상담 2곳을 두려면 어디가 좋아?')
  await page.keyboard.press('Enter')
  await page.waitForSelector('[data-fragment=headline]', { timeout: 15000 })
  await settle(page, 2500)
  await page.screenshot({ path: file('admin-map-춘천-sim-answer') })
  await page.close()
}

// ---- 현장 (390)
{
  const page = await newPage(MOBILE)
  await login(page, 'field')
  await settle(page, 2500)
  await fullShot(page, file('field-list'))
  const first = page.locator('a[href*="/field/cells/"]').first()
  if (await first.count()) {
    await first.click()
    await settle(page, 2000)
    await fullShot(page, file('field-cell'))
  }
  await page.setViewportSize(DESKTOP)
  await page.goto(`${BASE}/field`)
  await settle(page, 800)
  await page.getByRole('button', { name: /PC 화면/ }).click()
  await settle(page, 2500)
  await fullShot(page, file('field-list-desktop'))
  const firstD = page.locator('a[href*="/field/cells/"]').first()
  if (await firstD.count()) {
    await firstD.click()
    await settle(page, 2000)
    await fullShot(page, file('field-cell-desktop'))
  }
  await page.getByRole('button', { name: /모바일 화면/ }).click()
  await page.close()
}

await browser.close()
console.log(`saved to ${OUT}/ (prefix "${PREFIX}")`)
