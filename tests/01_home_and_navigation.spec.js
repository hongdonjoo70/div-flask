// @ts-check
import { test, expect } from '@playwright/test';

test.describe('메인 홈 및 헤더 네비게이션 테스트', () => {
  test('홈페이지 메인 타이틀, 로고, 슬로건 확인', async ({ page }) => {
    await page.goto('/');

    // 타이틀 확인
    await expect(page).toHaveTitle(/길마중/);

    // 로고 링크 및 슬로건
    const logoLink = page.locator('.logo-area a.logo-link');
    await expect(logoLink).toBeVisible();
    await expect(logoLink).toContainText('길마중');

    const slogan = page.locator('.logo-area .slogan');
    await expect(slogan).toBeVisible();
    await expect(slogan).toContainText('오늘, 더 특별한 여행');
  });

  test('상단 유틸리티 메뉴 (로그인, 예약확인, 고객센터) 링크 확인', async ({ page }) => {
    await page.goto('/');

    // 로그인 링크
    const loginLink = page.locator('.top-util-menu a[href*="/auth/login"]');
    await expect(loginLink).toBeVisible();

    // 예약확인 링크
    const lookupLink = page.locator('.top-util-menu a[href*="/order/lookup"]');
    await expect(lookupLink).toBeVisible();

    // 고객센터 링크
    const csLink = page.locator('.top-util-menu a[href*="/customer/faq"]');
    await expect(csLink).toBeVisible();
  });

  test('다국어 선택 드롭다운 토글 및 언어 목록 표시 확인', async ({ page }) => {
    await page.goto('/');

    const langBtn = page.locator('#languageDropdown');
    await expect(langBtn).toBeVisible();
    await expect(langBtn).toContainText('한국어');

    // 드롭다운 클릭 시 메뉴 목록 노출
    await langBtn.click();
    const langMenu = page.locator('#customLangMenu');
    await expect(langMenu).toBeVisible();

    // 다국어 옵션 4종 확인
    await expect(langMenu.locator('a:has-text("한국어")')).toBeVisible();
    await expect(langMenu.locator('a:has-text("English")')).toBeVisible();
    await expect(langMenu.locator('a:has-text("日本語")')).toBeVisible();
    await expect(langMenu.locator('a:has-text("简体中文")')).toBeVisible();
  });

  test('메인 홈 6대 권역 퀵 버튼 클릭 시 해당 권역으로 이동', async ({ page }) => {
    await page.goto('/');

    // 제주권 클릭
    const jejuBtn = page.locator('.icon-item:has-text("제주권")');
    await expect(jejuBtn).toBeVisible();
    await jejuBtn.click();

    // 제주권 상품 목록 페이지로 이동 및 탭 활성화 확인
    await expect(page).toHaveURL(/region=jeju/);
    const activeTab = page.locator('#pills-jeju-tab');
    await expect(activeTab).toHaveClass(/active/);
    await expect(page.locator('#pills-jeju .product-grid')).toBeVisible();
  });
});

