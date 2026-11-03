<template>
  <div
    class="app"
    :class="{ 'sidebar-open': sidebarOpen, 'sidebar-rail': railMode, 'layout-medium': isMedium }"
  >
    <aside id="app-sidebar" class="sidebar">
      <div class="sidebar-brand">
        <span class="brand-mark" aria-hidden="true">
          <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.75" stroke-linecap="round" stroke-linejoin="round">
            <path d="M21 8l-9-5-9 5v8l9 5 9-5V8z" />
            <path d="M3 8l9 5 9-5" />
            <path d="M12 13v8" />
          </svg>
        </span>
        <div class="brand-text">
          <span class="brand-name">{{ t('nav.companyName') }}</span>
          <span class="brand-subtitle">{{ t('nav.subtitle') }}</span>
        </div>
      </div>

      <nav class="sidebar-nav" :aria-label="t('nav.mainNavigation')">
        <div v-for="group in navGroups" :key="group.labelKey" class="nav-group">
          <div class="nav-group-label">{{ t(group.labelKey) }}</div>
          <router-link
            v-for="item in group.items"
            :key="item.path"
            :to="item.path"
            class="nav-item"
            :data-label="t(item.labelKey)"
            :active-class="item.path === '/' ? '' : 'active'"
            exact-active-class="active"
          >
            <svg class="nav-icon" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.75" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true">
              <path v-for="d in item.icon" :key="d" :d="d" />
            </svg>
            <span class="nav-label">{{ t(item.labelKey) }}</span>
          </router-link>
        </div>
      </nav>

      <div class="sidebar-footer">
        <span class="sidebar-version">v1.0</span>
        <button
          type="button"
          class="sidebar-collapse"
          :aria-expanded="railMode ? 'false' : 'true'"
          aria-controls="app-sidebar"
          :aria-label="railMode ? t('nav.expandSidebar') : t('nav.collapseSidebar')"
          :title="railMode ? t('nav.expandSidebar') : t('nav.collapseSidebar')"
          @click="toggleSidebar"
        >
          <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.75" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true">
            <path d="M11 17l-5-5 5-5" />
            <path d="M18 17l-5-5 5-5" />
          </svg>
        </button>
      </div>
    </aside>

    <div class="sidebar-backdrop" @click="sidebarOpen = false"></div>

    <div class="app-main">
      <header class="app-header">
        <div class="header-left">
          <button
            type="button"
            class="menu-toggle"
            :aria-expanded="sidebarOpen ? 'true' : 'false'"
            aria-controls="app-sidebar"
            :aria-label="t('nav.toggleMenu')"
            @click="sidebarOpen = !sidebarOpen"
          >
            <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.75" stroke-linecap="round" aria-hidden="true">
              <path d="M4 6h16M4 12h16M4 18h16" />
            </svg>
          </button>
          <nav class="breadcrumb" :aria-label="t('nav.breadcrumb')">
            <span class="breadcrumb-root">{{ t('nav.companyName') }}</span>
            <span class="breadcrumb-sep" aria-hidden="true">/</span>
            <span class="breadcrumb-current" aria-current="page">{{ currentPageKey ? t(currentPageKey) : '' }}</span>
          </nav>
        </div>
        <div class="header-right">
          <LanguageSwitcher />
          <ProfileMenu
            @show-profile-details="showProfileDetails = true"
            @show-tasks="showTasks = true"
          />
        </div>
      </header>
      <FilterBar />
      <main class="main-content">
        <div class="content-inner">
          <router-view />
        </div>
      </main>
    </div>

    <ProfileDetailsModal
      :is-open="showProfileDetails"
      @close="showProfileDetails = false"
    />

    <TasksModal
      :is-open="showTasks"
      :tasks="tasks"
      @close="showTasks = false"
      @add-task="addTask"
      @delete-task="deleteTask"
      @toggle-task="toggleTask"
    />
  </div>
</template>

<script>
import { ref, onMounted, onUnmounted, computed, watch } from 'vue'
import { useRoute } from 'vue-router'
import { api } from './api'
import { useAuth } from './composables/useAuth'
import { useI18n } from './composables/useI18n'
import FilterBar from './components/FilterBar.vue'
import ProfileMenu from './components/ProfileMenu.vue'
import ProfileDetailsModal from './components/ProfileDetailsModal.vue'
import TasksModal from './components/TasksModal.vue'
import LanguageSwitcher from './components/LanguageSwitcher.vue'

export default {
  name: 'App',
  components: {
    FilterBar,
    ProfileMenu,
    ProfileDetailsModal,
    TasksModal,
    LanguageSwitcher
  },
  setup() {
    const { currentUser } = useAuth()
    const { t } = useI18n()
    const showProfileDetails = ref(false)
    const showTasks = ref(false)
    const apiTasks = ref([])
    const route = useRoute()

    // Sidebar navigation; each icon is a list of 24x24 stroke paths
    const navGroups = [
      {
        labelKey: 'nav.groupOperations',
        items: [
          { path: '/', labelKey: 'nav.overview', icon: ['M3 3h7v9H3z', 'M14 3h7v5h-7z', 'M14 12h7v9h-7z', 'M3 16h7v5H3z'] },
          { path: '/inventory', labelKey: 'nav.inventory', icon: ['M21 8l-9-5-9 5v8l9 5 9-5V8z', 'M3 8l9 5 9-5', 'M12 13v8'] },
          { path: '/orders', labelKey: 'nav.orders', icon: ['M6 2L3 6v14a2 2 0 002 2h14a2 2 0 002-2V6l-3-4z', 'M3 6h18', 'M16 10a4 4 0 01-8 0'] },
          { path: '/spending', labelKey: 'nav.finance', icon: ['M12 2v20', 'M17 5H9.5a3.5 3.5 0 000 7h5a3.5 3.5 0 010 7H6'] }
        ]
      },
      {
        labelKey: 'nav.groupPlanning',
        items: [
          { path: '/demand', labelKey: 'nav.demandForecast', icon: ['M3 3v18h18', 'M7 14l4-4 4 4 5-5'] },
          { path: '/restocking', labelKey: 'nav.restocking', icon: ['M21 12a9 9 0 11-3-6.7', 'M21 3v6h-6'] },
          { path: '/reports', labelKey: 'nav.reports', icon: ['M14 2H6a2 2 0 00-2 2v16a2 2 0 002 2h12a2 2 0 002-2V8z', 'M14 2v6h6', 'M8 13h8', 'M8 17h5'] }
        ]
      }
    ]

    // Breadcrumb label for the current route, looked up from the nav array
    const currentPageKey = computed(() => {
      const item = navGroups.flatMap(g => g.items).find(i => i.path === route.path)
      return item ? item.labelKey : null
    })

    // Sidebar has three layouts, picked by viewport width:
    //   >= 1280px  full sidebar; the user can collapse it to an icon rail (remembered)
    //   768-1279px icon rail; "expand" opens the full sidebar as an overlay
    //   < 768px    hidden; the header hamburger opens it as an off-canvas drawer
    // sidebarOpen drives the overlay/drawer, sidebarCollapsed the desktop preference.
    const COLLAPSED_KEY = 'sidebar-collapsed'
    const mobileQuery = window.matchMedia('(max-width: 767px)')
    const mediumDownQuery = window.matchMedia('(max-width: 1279px)')
    const isMobile = ref(mobileQuery.matches)
    const isMediumDown = ref(mediumDownQuery.matches)
    const isMedium = computed(() => isMediumDown.value && !isMobile.value)

    const sidebarOpen = ref(false)
    const sidebarCollapsed = ref(false)
    try {
      sidebarCollapsed.value = localStorage.getItem(COLLAPSED_KEY) === 'true'
    } catch (e) {
      // Storage can be unavailable (private mode); fall back to expanded
    }

    const railMode = computed(() => {
      if (isMobile.value) return false
      if (isMedium.value) return !sidebarOpen.value
      return sidebarCollapsed.value
    })

    const toggleSidebar = () => {
      if (isMedium.value) {
        sidebarOpen.value = !sidebarOpen.value
        return
      }
      sidebarCollapsed.value = !sidebarCollapsed.value
      try {
        localStorage.setItem(COLLAPSED_KEY, String(sidebarCollapsed.value))
      } catch (e) {
        // Preference just won't persist
      }
    }

    // An overlay/drawer left open must not carry over into another layout
    // (e.g. a drawer opened on mobile showing a backdrop on desktop)
    const onBreakpointChange = () => {
      isMobile.value = mobileQuery.matches
      isMediumDown.value = mediumDownQuery.matches
      sidebarOpen.value = false
    }

    // Close the drawer whenever the user navigates to another page
    watch(() => route.path, () => {
      sidebarOpen.value = false
    })

    const onKeydown = (e) => {
      if (e.key === 'Escape') sidebarOpen.value = false
    }

    // Merge mock tasks from currentUser with API tasks
    const tasks = computed(() => {
      return [...currentUser.value.tasks, ...apiTasks.value]
    })

    const loadTasks = async () => {
      try {
        apiTasks.value = await api.getTasks()
      } catch (err) {
        console.error('Failed to load tasks:', err)
      }
    }

    const addTask = async (taskData) => {
      try {
        const newTask = await api.createTask(taskData)
        // Add new task to the beginning of the array
        apiTasks.value.unshift(newTask)
      } catch (err) {
        console.error('Failed to add task:', err)
      }
    }

    const deleteTask = async (taskId) => {
      try {
        // Check if it's a mock task (from currentUser)
        const isMockTask = currentUser.value.tasks.some(t => t.id === taskId)

        if (isMockTask) {
          // Remove from mock tasks
          const index = currentUser.value.tasks.findIndex(t => t.id === taskId)
          if (index !== -1) {
            currentUser.value.tasks.splice(index, 1)
          }
        } else {
          // Remove from API tasks
          await api.deleteTask(taskId)
          apiTasks.value = apiTasks.value.filter(t => t.id !== taskId)
        }
      } catch (err) {
        console.error('Failed to delete task:', err)
      }
    }

    const toggleTask = async (taskId) => {
      try {
        // Check if it's a mock task (from currentUser)
        const mockTask = currentUser.value.tasks.find(t => t.id === taskId)

        if (mockTask) {
          // Toggle mock task status
          mockTask.status = mockTask.status === 'pending' ? 'completed' : 'pending'
        } else {
          // Toggle API task
          const updatedTask = await api.toggleTask(taskId)
          const index = apiTasks.value.findIndex(t => t.id === taskId)
          if (index !== -1) {
            apiTasks.value[index] = updatedTask
          }
        }
      } catch (err) {
        console.error('Failed to toggle task:', err)
      }
    }

    onMounted(() => {
      loadTasks()
      document.addEventListener('keydown', onKeydown)
      mobileQuery.addEventListener('change', onBreakpointChange)
      mediumDownQuery.addEventListener('change', onBreakpointChange)
    })

    onUnmounted(() => {
      document.removeEventListener('keydown', onKeydown)
      mobileQuery.removeEventListener('change', onBreakpointChange)
      mediumDownQuery.removeEventListener('change', onBreakpointChange)
    })

    return {
      t,
      navGroups,
      currentPageKey,
      sidebarOpen,
      railMode,
      isMedium,
      toggleSidebar,
      showProfileDetails,
      showTasks,
      tasks,
      addTask,
      deleteTask,
      toggleTask
    }
  }
}
</script>

<style>
:root {
  /* spacing: 4px base */
  --space-1: 4px;  --space-2: 8px;  --space-3: 12px; --space-4: 16px;
  --space-5: 20px; --space-6: 24px; --space-8: 32px; --space-10: 40px;

  /* surfaces and text */
  --color-bg: #f8fafc;  --color-surface: #ffffff;  --color-surface-muted: #f1f5f9;
  --color-border: #e2e8f0;  --color-border-strong: #cbd5e1;
  --color-text: #0f172a;  --color-text-secondary: #334155;
  --color-text-muted: #64748b;  --color-text-subtle: #94a3b8;

  /* accent and status: base / soft background / strong text (for badges) */
  --color-accent: #2563eb;   --color-accent-hover: #1d4ed8;  --color-accent-soft: #eff6ff;  --color-accent-strong: #1e40af;
  --color-success: #16a34a;  --color-success-soft: #f0fdf4;  --color-success-strong: #166534;
  --color-warning: #d97706;  --color-warning-soft: #fffbeb;  --color-warning-strong: #92400e;
  --color-danger: #dc2626;   --color-danger-soft: #fef2f2;   --color-danger-strong: #991b1b;
  --color-info: #0284c7;     --color-info-soft: #f0f9ff;     --color-info-strong: #075985;
  --color-neutral-soft: #f1f5f9;  --color-neutral-strong: #475569;

  /* charts keep their existing hues, so data colours don't shift meaning */
  --chart-blue: #3b82f6; --chart-green: #10b981; --chart-amber: #f59e0b;
  --chart-red: #ef4444;  --chart-slate: #64748b; --chart-violet: #8b5cf6;

  /* type */
  --font-sans: 'Inter', -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
  --text-xs: 12px; --text-sm: 13px; --text-base: 14px; --text-md: 16px;
  --text-lg: 18px; --text-xl: 22px; --text-2xl: 28px;

  /* shape and depth */
  --radius-sm: 6px; --radius-md: 8px; --radius-lg: 12px; --radius-full: 999px;
  --shadow-sm: 0 1px 2px rgba(15, 23, 42, 0.04);
  --shadow-md: 0 1px 3px rgba(15, 23, 42, 0.06), 0 1px 2px rgba(15, 23, 42, 0.04);
  --shadow-lg: 0 12px 32px rgba(15, 23, 42, 0.12);
  --focus-ring: 0 0 0 3px var(--color-accent-soft);

  /* layout and layering */
  --sidebar-width: 240px; --sidebar-rail-width: 72px; --header-height: 64px; --content-max: 1440px;
  --z-filterbar: 45; --z-header: 50; --z-backdrop: 55; --z-sidebar: 60;
  --z-dropdown: 1000; --z-modal: 2000;
}

* {
  margin: 0;
  padding: 0;
  box-sizing: border-box;
}

body {
  font-family: var(--font-sans);
  font-size: var(--text-base);
  background: var(--color-bg);
  color: var(--color-text);
  -webkit-font-smoothing: antialiased;
  -moz-osx-font-smoothing: grayscale;
}

.app {
  display: flex;
  flex-direction: column;
  min-height: 100vh;
}

/* ---------- Sidebar ---------- */
.sidebar {
  position: fixed;
  top: 0;
  left: 0;
  bottom: 0;
  width: var(--sidebar-width);
  display: flex;
  flex-direction: column;
  background: var(--color-surface);
  border-right: 1px solid var(--color-border);
  z-index: var(--z-sidebar);
  overflow-y: auto;
  overflow-x: hidden;
  transition: width 0.2s ease, transform 0.2s ease, box-shadow 0.2s ease;
}

.sidebar-brand {
  display: flex;
  align-items: flex-start;
  gap: var(--space-3);
  padding: var(--space-5) var(--space-5) var(--space-4);
}

.brand-mark {
  flex-shrink: 0;
  display: flex;
  align-items: center;
  justify-content: center;
  width: 32px;
  height: 32px;
  border-radius: var(--radius-md);
  background: var(--color-accent);
  color: #ffffff;
}

.brand-mark svg {
  width: 18px;
  height: 18px;
}

.brand-text {
  display: flex;
  flex-direction: column;
  min-width: 0;
}

.brand-name {
  font-size: var(--text-base);
  font-weight: 700;
  color: var(--color-text);
  letter-spacing: -0.01em;
  line-height: 1.3;
}

.brand-subtitle {
  font-size: var(--text-xs);
  color: var(--color-text-muted);
  line-height: 1.35;
  margin-top: 2px;
}

.sidebar-nav {
  flex: 1;
  padding: var(--space-2) var(--space-3);
  display: flex;
  flex-direction: column;
  gap: var(--space-5);
}

.nav-group {
  display: flex;
  flex-direction: column;
  gap: 2px;
}

.nav-group-label {
  padding: 0 var(--space-3) var(--space-2);
  font-size: 11px;
  font-weight: 600;
  text-transform: uppercase;
  letter-spacing: 0.06em;
  color: var(--color-text-subtle);
}

.nav-item {
  position: relative;
  display: flex;
  align-items: center;
  gap: var(--space-3);
  height: 36px;
  padding: 0 var(--space-3);
  border-radius: var(--radius-md);
  color: var(--color-text-secondary);
  font-size: var(--text-base);
  font-weight: 500;
  text-decoration: none;
  transition: background-color 0.15s ease, color 0.15s ease;
}

.nav-item:hover {
  background: var(--color-surface-muted);
  color: var(--color-text);
}

.nav-item:focus-visible {
  outline: none;
  box-shadow: var(--focus-ring);
}

.nav-item.active {
  background: var(--color-accent-soft);
  color: var(--color-accent);
}

/* 3px accent bar on the left edge of the active item */
.nav-item.active::before {
  content: '';
  position: absolute;
  left: calc(-1 * var(--space-3));
  top: 6px;
  bottom: 6px;
  width: 3px;
  border-radius: 0 3px 3px 0;
  background: var(--color-accent);
}

.nav-icon {
  flex-shrink: 0;
  width: 20px;
  height: 20px;
}

.nav-label {
  min-width: 0;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.sidebar-footer {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: var(--space-2);
  padding: var(--space-3) var(--space-3) var(--space-3) var(--space-5);
  font-size: var(--text-xs);
  color: var(--color-text-subtle);
  border-top: 1px solid var(--color-border);
}

.sidebar-collapse {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  width: 32px;
  height: 32px;
  flex-shrink: 0;
  border: none;
  border-radius: var(--radius-md);
  background: transparent;
  color: var(--color-text-muted);
  cursor: pointer;
  transition: background-color 0.15s ease, color 0.15s ease;
}

.sidebar-collapse:hover {
  background: var(--color-surface-muted);
  color: var(--color-text);
}

.sidebar-collapse:focus-visible {
  outline: none;
  box-shadow: var(--focus-ring);
}

.sidebar-collapse svg {
  width: 18px;
  height: 18px;
  transition: transform 0.2s ease;
}

.sidebar-backdrop {
  display: none;
}

/* Overlay/drawer backdrop, used by the medium-width overlay and the mobile drawer */
.sidebar-open .sidebar-backdrop {
  display: block;
  position: fixed;
  inset: 0;
  background: rgba(15, 23, 42, 0.4);
  z-index: var(--z-backdrop);
}

/* ---------- Icon rail (collapsed sidebar) ---------- */
.sidebar-rail .sidebar {
  width: var(--sidebar-rail-width);
  /* Visible overflow lets the hover tooltips extend past the rail; the seven
     nav items fit the viewport height, so nothing needs to scroll */
  overflow: visible;
}

.sidebar-rail .brand-text,
.sidebar-rail .sidebar-version {
  display: none;
}

/* Group headings collapse to thin dividers; the text stays for screen readers */
.sidebar-rail .nav-group-label {
  height: 1px;
  padding: 0;
  margin: 0 var(--space-2) var(--space-2);
  overflow: hidden;
  color: transparent;
  background: var(--color-border);
}

.sidebar-rail .nav-group:first-child .nav-group-label {
  background: transparent;
}

.sidebar-rail .nav-item {
  justify-content: center;
  padding: 0;
}

/* Visually hidden, but still the link's accessible name */
.sidebar-rail .nav-label {
  position: absolute;
  width: 1px;
  height: 1px;
  overflow: hidden;
  clip: rect(0 0 0 0);
  white-space: nowrap;
}

/* Tooltip with the page name, shown on hover and keyboard focus */
.sidebar-rail .nav-item::after {
  content: attr(data-label);
  position: absolute;
  left: calc(100% + var(--space-3));
  top: 50%;
  transform: translateY(-50%);
  padding: var(--space-1) var(--space-2);
  border-radius: var(--radius-sm);
  background: var(--color-text);
  color: #ffffff;
  font-size: var(--text-xs);
  font-weight: 500;
  white-space: nowrap;
  box-shadow: var(--shadow-md);
  opacity: 0;
  pointer-events: none;
  transition: opacity 0.12s ease;
}

.sidebar-rail .nav-item:hover::after,
.sidebar-rail .nav-item:focus-visible::after {
  opacity: 1;
}

.sidebar-rail .sidebar-footer {
  justify-content: center;
  padding: var(--space-3) 0;
}

/* Chevrons point left to collapse, right to expand */
.sidebar-rail .sidebar-collapse svg {
  transform: rotate(180deg);
}

.sidebar-rail .app-main {
  margin-left: var(--sidebar-rail-width);
}

/* ---------- Main column ---------- */
.app-main {
  flex: 1;
  display: flex;
  flex-direction: column;
  margin-left: var(--sidebar-width);
  min-width: 0;
  transition: margin-left 0.2s ease;
}

.app-header {
  position: sticky;
  top: 0;
  z-index: var(--z-header);
  height: var(--header-height);
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: var(--space-4);
  padding: 0 var(--space-8);
  background: var(--color-surface);
  border-bottom: 1px solid var(--color-border);
}

.header-left,
.header-right {
  display: flex;
  align-items: center;
  gap: var(--space-3);
  min-width: 0;
}

.menu-toggle {
  display: none;
  align-items: center;
  justify-content: center;
  width: 36px;
  height: 36px;
  flex-shrink: 0;
  border: 1px solid var(--color-border);
  border-radius: var(--radius-md);
  background: var(--color-surface);
  color: var(--color-text-secondary);
  cursor: pointer;
}

.menu-toggle:hover {
  background: var(--color-surface-muted);
}

.menu-toggle:focus-visible {
  outline: none;
  border-color: var(--color-accent);
  box-shadow: var(--focus-ring);
}

.menu-toggle svg {
  width: 20px;
  height: 20px;
}

.breadcrumb {
  display: flex;
  align-items: center;
  gap: var(--space-2);
  min-width: 0;
  font-size: var(--text-base);
  white-space: nowrap;
}

.breadcrumb-root {
  color: var(--color-text-muted);
  overflow: hidden;
  text-overflow: ellipsis;
}

.breadcrumb-sep {
  color: var(--color-border-strong);
}

.breadcrumb-current {
  color: var(--color-text);
  font-weight: 600;
}

.main-content {
  flex: 1;
  width: 100%;
}

.content-inner {
  max-width: var(--content-max);
  margin: 0 auto;
  padding: var(--space-8);
}

/* ---------- Page header ---------- */
.page-header {
  margin-bottom: var(--space-6);
}

.page-header h2 {
  font-size: var(--text-2xl);
  font-weight: 700;
  color: var(--color-text);
  margin-bottom: var(--space-1);
  letter-spacing: -0.02em;
  line-height: 1.25;
}

.page-header p {
  color: var(--color-text-muted);
  font-size: var(--text-base);
}

/* ---------- Stat cards ---------- */
.stats-grid {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(min(100%, 240px), 1fr));
  gap: var(--space-4);
  margin-bottom: var(--space-6);
}

.stat-card {
  position: relative;
  background: var(--color-surface);
  padding: var(--space-5);
  border-radius: var(--radius-lg);
  border: 1px solid var(--color-border);
  box-shadow: var(--shadow-sm);
  transition: border-color 0.15s ease, box-shadow 0.15s ease;
}

.stat-card:hover {
  border-color: var(--color-border-strong);
  box-shadow: var(--shadow-md);
}

.stat-label {
  display: flex;
  align-items: center;
  gap: var(--space-2);
  color: var(--color-text-muted);
  font-size: var(--text-sm);
  font-weight: 500;
  margin-bottom: var(--space-2);
}

.stat-value {
  font-size: var(--text-2xl);
  font-weight: 600;
  color: var(--color-text);
  letter-spacing: -0.02em;
  line-height: 1.2;
  font-variant-numeric: tabular-nums;
}

/* Status variants: a small coloured dot before the label, not a coloured value */
.stat-card.success .stat-label::before,
.stat-card.warning .stat-label::before,
.stat-card.danger .stat-label::before,
.stat-card.info .stat-label::before {
  content: '';
  flex-shrink: 0;
  width: 8px;
  height: 8px;
  border-radius: var(--radius-full);
}

.stat-card.success .stat-label::before { background: var(--color-success); }
.stat-card.warning .stat-label::before { background: var(--color-warning); }
.stat-card.danger .stat-label::before { background: var(--color-danger); }
.stat-card.info .stat-label::before { background: var(--color-info); }

/* ---------- Cards ---------- */
.card {
  --card-pad: var(--space-6);
  background: var(--color-surface);
  border-radius: var(--radius-lg);
  padding: var(--card-pad);
  border: 1px solid var(--color-border);
  box-shadow: var(--shadow-sm);
  margin-bottom: var(--space-6);
  min-width: 0;
}

/* Full-bleed header: cancels the card padding so its border spans edge to edge */
.card-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  gap: var(--space-3);
  flex-wrap: wrap;
  margin: calc(-1 * var(--card-pad)) calc(-1 * var(--card-pad)) var(--card-pad);
  padding: var(--space-5) var(--card-pad);
  border-bottom: 1px solid var(--color-border);
}

.card-title {
  font-size: var(--text-md);
  font-weight: 600;
  color: var(--color-text);
  letter-spacing: -0.01em;
}

/* ---------- Tables ---------- */
.table-container {
  overflow-x: auto;
}

table {
  width: 100%;
  border-collapse: collapse;
}

thead {
  background: var(--color-surface-muted);
}

th {
  text-align: left;
  padding: var(--space-3) var(--space-4);
  font-weight: 600;
  color: var(--color-text-muted);
  font-size: var(--text-xs);
  background: var(--color-surface-muted);
  border-bottom: 1px solid var(--color-border);
  white-space: nowrap;
}

td {
  padding: var(--space-3) var(--space-4);
  border-bottom: 1px solid var(--color-border);
  color: var(--color-text-secondary);
  font-size: var(--text-base);
}

tbody tr:last-child td {
  border-bottom: none;
}

tbody tr {
  transition: background-color 0.15s ease;
}

tbody tr:hover {
  background: var(--color-surface-muted);
}

/* A table that sits directly in a card runs edge to edge: it cancels the card
   padding on the sides and bottom, and its outer cells pick the padding back up */
.card > .table-container {
  margin-left: calc(-1 * var(--card-pad));
  margin-right: calc(-1 * var(--card-pad));
}

.card > .table-container:last-child {
  margin-bottom: calc(-1 * var(--card-pad));
  border-radius: 0 0 var(--radius-lg) var(--radius-lg);
}

.card > .card-header + .table-container {
  margin-top: calc(-1 * var(--card-pad));
}

.card > .table-container th:first-child,
.card > .table-container td:first-child {
  padding-left: var(--card-pad);
}

.card > .table-container th:last-child,
.card > .table-container td:last-child {
  padding-right: var(--card-pad);
}

th.num,
td.num {
  text-align: right;
  font-variant-numeric: tabular-nums;
}

.clickable-cell {
  cursor: pointer;
}

/* ---------- Badges ---------- */
.badge {
  display: inline-flex;
  align-items: center;
  padding: 2px var(--space-2);
  border-radius: var(--radius-full);
  font-size: var(--text-xs);
  font-weight: 500;
  line-height: 18px;
  white-space: nowrap;
  background: var(--color-neutral-soft);
  color: var(--color-neutral-strong);
}

.badge.success,
.badge.increasing {
  background: var(--color-success-soft);
  color: var(--color-success-strong);
  box-shadow: inset 0 0 0 1px rgba(22, 163, 74, 0.15);
}

.badge.warning,
.badge.medium {
  background: var(--color-warning-soft);
  color: var(--color-warning-strong);
  box-shadow: inset 0 0 0 1px rgba(217, 119, 6, 0.18);
}

.badge.danger,
.badge.decreasing,
.badge.high {
  background: var(--color-danger-soft);
  color: var(--color-danger-strong);
  box-shadow: inset 0 0 0 1px rgba(220, 38, 38, 0.15);
}

.badge.info,
.badge.low {
  background: var(--color-info-soft);
  color: var(--color-info-strong);
  box-shadow: inset 0 0 0 1px rgba(2, 132, 199, 0.15);
}

.badge.stable {
  background: var(--color-neutral-soft);
  color: var(--color-neutral-strong);
  box-shadow: inset 0 0 0 1px rgba(71, 85, 105, 0.12);
}

/* ---------- Buttons and inputs ---------- */
.btn,
.btn-primary,
.btn-secondary {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  gap: var(--space-2);
  height: 36px;
  padding: 0 var(--space-4);
  border-radius: var(--radius-md);
  font-family: inherit;
  font-size: var(--text-base);
  font-weight: 500;
  cursor: pointer;
  transition: background-color 0.15s ease, border-color 0.15s ease, box-shadow 0.15s ease;
}

.btn-primary {
  background: var(--color-accent);
  border: 1px solid var(--color-accent);
  color: #ffffff;
}

.btn-primary:hover:not(:disabled) {
  background: var(--color-accent-hover);
  border-color: var(--color-accent-hover);
}

.btn-secondary {
  background: var(--color-surface);
  border: 1px solid var(--color-border-strong);
  color: var(--color-text-secondary);
}

.btn-secondary:hover:not(:disabled) {
  background: var(--color-surface-muted);
}

.btn:focus-visible,
.btn-primary:focus-visible,
.btn-secondary:focus-visible {
  outline: none;
  border-color: var(--color-accent);
  box-shadow: var(--focus-ring);
}

.btn:disabled,
.btn-primary:disabled,
.btn-secondary:disabled {
  opacity: 0.5;
  cursor: not-allowed;
}

/* ---------- Loading and error states ---------- */
.loading {
  text-align: center;
  padding: var(--space-10);
  color: var(--color-text-muted);
  font-size: var(--text-base);
}

.error {
  background: var(--color-danger-soft);
  border: 1px solid rgba(220, 38, 38, 0.2);
  color: var(--color-danger-strong);
  padding: var(--space-4);
  border-radius: var(--radius-md);
  margin: var(--space-4) 0;
  font-size: var(--text-base);
}

/* ---------- Medium widths: rail by default, full sidebar as an overlay ---------- */
/* The content keeps the rail's margin while the overlay is open, so the page
   doesn't shift underneath it */
.layout-medium .app-main {
  margin-left: var(--sidebar-rail-width);
}

.layout-medium.sidebar-open .sidebar {
  box-shadow: var(--shadow-lg);
}

@media (max-width: 1023px) {
  .app-header {
    padding: 0 var(--space-4);
  }

  .content-inner {
    padding: var(--space-6) var(--space-4);
  }
}

/* ---------- Mobile: sidebar becomes an off-canvas drawer ---------- */
@media (max-width: 767px) {
  .sidebar {
    transform: translateX(-100%);
    box-shadow: none;
  }

  .sidebar-open .sidebar {
    transform: translateX(0);
    box-shadow: var(--shadow-lg);
  }

  .app-main {
    margin-left: 0;
  }

  .menu-toggle {
    display: inline-flex;
  }

  /* The drawer closes via backdrop, Escape or navigation; no collapse control */
  .sidebar-collapse {
    display: none;
  }
}

@media (max-width: 640px) {
  .breadcrumb-root,
  .breadcrumb-sep {
    display: none;
  }
}
</style>
