document.addEventListener("DOMContentLoaded", function () {
  const sidebar = document.querySelector(".sidebar");
  const sidebarToggle = document.getElementById("sidebar-toggle");
  const mainContent = document.querySelector(".main-content"); // Not strictly needed for margin if using CSS sibling selector
  const themeToggleButton = document.getElementById("theme-toggle-button");
  const themeIcon = themeToggleButton.querySelector(".nav-icon");

  // 1. 侧边栏伸缩控制
  sidebarToggle.addEventListener("click", () => {
    sidebar.classList.toggle("collapsed");
    // Update toggle button icon (optional)
    if (sidebar.classList.contains("collapsed")) {
      sidebarToggle.innerHTML = '<i class="fas fa-bars"></i>';
    } else {
      sidebarToggle.innerHTML = '<i class="fas fa-times"></i>'; // Change to a close icon
    }
  });

  // 2. 主题切换功能
  const themes = ["system", "light", "dark"];
  const themeLabels = {
    system: "跟随系统",
    light: "日间模式",
    dark: "夜间模式",
  };
  const themeIcons = {
    system: "fas fa-desktop", // 电脑图标
    light: "fas fa-sun", // 太阳图标
    dark: "fas fa-moon", // 月亮图标
  };

  let currentThemeIndex = 0; // Default to 'system'

  function applyTheme(theme) {
    document.documentElement.setAttribute("data-theme", theme);

    // Update button text and icon
    const buttonTextSpan = themeToggleButton.querySelector(".nav-text");
    if (buttonTextSpan) {
      // Make sure span exists
      buttonTextSpan.textContent = themeLabels[theme];
    }
    themeIcon.className = `nav-icon ${themeIcons[theme]}`; // Update icon class

    localStorage.setItem("theme", theme);
    // Update currentThemeIndex based on the applied theme
    currentThemeIndex = themes.indexOf(theme);
  }

  themeToggleButton.addEventListener("click", () => {
    currentThemeIndex = (currentThemeIndex + 1) % themes.length;
    const nextTheme = themes[currentThemeIndex];
    applyTheme(nextTheme);
  });

  // 页面加载时应用保存的主题或系统偏好
  const savedTheme = localStorage.getItem("theme");
  if (savedTheme && themes.includes(savedTheme)) {
    applyTheme(savedTheme);
  } else {
    // Default to 'system' if no valid theme saved or first visit
    applyTheme("system");
  }

  // 监听系统颜色方案变化，如果当前是“跟随系统”模式
  if (window.matchMedia) {
    const colorSchemeQuery = window.matchMedia("(prefers-color-scheme: dark)");

    function handleSystemThemeChange(e) {
      if (document.documentElement.getAttribute("data-theme") === "system") {
        // No need to call applyTheme as CSS media queries handle it.
        // Just ensuring the UI elements (like button text/icon) could be updated if necessary.
        // For this setup, applyTheme('system') mainly updates the button and localStorage.
        // If system changes, and we are set to system, our appearance changes via CSS,
        // but the button text and icon should remain "跟随系统".
        // So, this listener is more for future enhancements or if specific JS actions are needed.
        console.log(
          'System theme changed, current theme is "system". CSS handles appearance.'
        );
      }
    }

    try {
      // Chrome & Firefox
      colorSchemeQuery.addEventListener("change", handleSystemThemeChange);
    } catch (e1) {
      try {
        // Safari
        colorSchemeQuery.addListener(handleSystemThemeChange);
      } catch (e2) {
        console.error("Error adding listener for system theme changes.");
      }
    }
  }
});
