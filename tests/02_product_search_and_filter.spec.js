// @ts-check
import { test, expect } from '@playwright/test';

test.describe('여행 상품 탐색, 권역 필터링 및 상세 페이지 테스트', () => {
  test('전체 상품 목록 로드 및 권역 탭 전환 동작 확인', async ({ page }) => {
    await page.goto('/product/main_product');

    // 기본 '전체' 탭 활성화 확인
    const allTab = page.locator('#pills-all-tab');
    await expect(allTab).toHaveClass(/active/);
    await expect(page.locator('#pills-all .product-grid .card').first()).toBeVisible();

    // '강원권' 탭 버튼 클릭
    const gangwonTab = page.locator('#pills-gang-tab');
    await gangwonTab.click();
    await expect(gangwonTab).toHaveClass(/active/);
    await expect(page.locator('#pills-gang .product-grid')).toBeVisible();

    // '충청권' 탭 버튼 클릭
    const chungcheongTab = page.locator('#pills-chung-tab');
    await chungcheongTab.click();
    await expect(chungcheongTab).toHaveClass(/active/);
    await expect(page.locator('#pills-chung .product-grid')).toBeVisible();
  });

  test('키워드 검색 정상 결과 노출 확인', async ({ page }) => {
    await page.goto('/product/main_product');

    // 검색창에 '제주' 입력 후 제출
    const searchInput = page.locator('input.header-search-input');
    await searchInput.fill('제주');
    await page.locator('button.header-search-btn').click();

    // 결과 텍스트 확인
    await expect(page.locator('#main_text')).toContainText('제주');
    await expect(page.locator('#main_text')).toContainText('검색 결과');

    // 결과 상품 카드 확인
    const cards = page.locator('.tab-pane.active .product-grid .card');
    await expect(cards.first()).toBeVisible();
    const firstTitle = await cards.first().locator('.card-title').textContent();
    expect(firstTitle).toContain('제주');
  });

  test('검색 결과 없는 키워드 처리 및 안내 문구 노출', async ({ page }) => {
    await page.goto('/product/main_product');

    // 결과가 없을 만한 임의의 키워드 입력
    const searchInput = page.locator('input.header-search-input');
    await searchInput.fill('존재하지않는여행지12345');
    await page.locator('button.header-search-btn').click();

    // '검색 결과가 없습니다' 안내 표시 확인
    const noResultMsg = page.locator('.tab-pane.active');
    await expect(noResultMsg).toContainText('검색 결과가 없습니다');
    await expect(page.locator('a:has-text("전체 여행 상품 보기")').first()).toBeVisible();
  });

  test('상품 상세 페이지 진입 및 상세 정보/일정/예약 버튼 확인', async ({ page }) => {
    await page.goto('/product/main_product');

    // 첫 번째 카드의 '상세보기' 클릭
    const detailLink = page.locator('.tab-pane.active .product-grid .card a.btn-primary:has-text("상세보기")').first();
    await detailLink.click();

    // 상세 페이지로 이동 확인
    await expect(page).toHaveURL(/\/product\/sub_product\/\d+/);

    // 상품명 및 가격 영역 노출 확인
    await expect(page.locator('.tour-hero, h1, h2, .product-title').first()).toBeVisible();

    // '바로 구매하기' 버튼 클릭 시 예약 페이지로 이동 확인
    const purchaseBtn = page.locator('#people button:has-text("구매하기")');
    await expect(purchaseBtn).toBeVisible();
    await purchaseBtn.click();

    await expect(page).toHaveURL(/\/order\/reserve\?product_id=\d+/);
  });
});
