/**
 * 22-tabs-handler.js
 * Gestiona la navegación entre tabs del sidebar y muestra/oculta el contenido correspondiente.
 * Conecta con los componentes de proyectos y otras secciones.
 */

(function() {
  'use strict';

  // ────────────────────────────────────────────────────────────────────────────
  // Tab Management
  // ────────────────────────────────────────────────────────────────────────────

  const TAB_STATE = {
    activeTab: 'pane-archivo',
  };

  function selectTab(tabName) {
    TAB_STATE.activeTab = tabName;

    // Update tab button active state
    document.querySelectorAll('.sidebar-tab').forEach((btn) => {
      btn.classList.toggle('active', btn.dataset.pane === tabName);
    });

    // Hide/show sections
    const contentShell = document.querySelector('.content-shell');
    const projectsSection = document.getElementById('projects-section');

    if (tabName === 'pane-proyectos') {
      if (contentShell) contentShell.style.display = 'none';
      if (projectsSection) projectsSection.style.display = 'block';
      // Load projects when tab is clicked
      if (window.ProjectsUI && window.ProjectsUI.loadAndRenderProjects) {
        window.ProjectsUI.loadAndRenderProjects();
      }
    } else {
      if (contentShell) contentShell.style.display = 'block';
      if (projectsSection) projectsSection.style.display = 'none';
    }
  }

  // ────────────────────────────────────────────────────────────────────────────
  // Init
  // ────────────────────────────────────────────────────────────────────────────

  window.addEventListener('DOMContentLoaded', () => {
    // Setup tab click handlers
    document.querySelectorAll('.sidebar-tab').forEach((tab) => {
      tab.addEventListener('click', () => {
        const tabName = tab.dataset.pane;
        selectTab(tabName);
      });
    });

    // Restore saved tab state from localStorage
    try {
      const savedTab = localStorage.getItem('active-tab');
      if (savedTab) {
        selectTab(savedTab);
      }
    } catch (e) {
      console.warn('No se pudo restaurar el tab guardado:', e);
    }
  });

  // Override selectTab to save state
  const originalSelectTab = selectTab;
  window.selectTab = function(tabName) {
    originalSelectTab(tabName);
    try {
      localStorage.setItem('active-tab', tabName);
    } catch (e) {
      console.warn('No se pudo guardar el tab:', e);
    }
  };

  // Export
  window.TabManager = {
    selectTab: window.selectTab,
    getActiveTab: () => TAB_STATE.activeTab,
  };
})();
