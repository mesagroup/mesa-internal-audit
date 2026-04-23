import { Component, OnInit, HostListener } from '@angular/core';
import { Router, NavigationEnd } from '@angular/router';
import { filter } from 'rxjs/operators';

export interface NavItem {
  label: string;
  icon: string;
  route?: string;
  children?: NavItem[];
  badge?: number;
  permission?: string;
}

@Component({
  selector: 'app-sidebar',
  templateUrl: './sidebar.component.html',
  styleUrls: ['./sidebar.component.scss']
})
export class SidebarComponent implements OnInit {

  /** true = sidebar a 48px (solo icone), false = 240px (expanded) */
  collapsed = false;

  /** Stato espansione sottomenu: chiave = label del gruppo */
  expandedGroups: Record<string, boolean> = {};

  /** Route attiva corrente */
  activeRoute = '';

  /** Mobile drawer aperto */
  mobileDrawerOpen = false;

  /** Iniziali utente per avatar */
  userInitials = 'AM';
  userName = 'Amministratore';

  /** Notifiche badge */
  notificationCount = 0;

  // ──────────────────────────────────────────────
  // Struttura navigazione PROCOMP
  // ──────────────────────────────────────────────
  navItems: NavItem[] = [
    {
      label: 'Dashboard',
      icon: 'dashboard',
      route: '/dashboard'
    },
    {
      label: 'Campagne',
      icon: 'campaign',
      route: '/campagne'
    },
    {
      label: 'Controlli',
      icon: 'fact_check',
      route: '/controlli'
    },
    {
      label: 'Validazione',
      icon: 'verified',
      route: '/validazione'
    },
    {
      label: 'Gap',
      icon: 'warning_amber',
      route: '/gap'
    },
    {
      label: 'Report',
      icon: 'bar_chart',
      route: '/report'
    },
    {
      label: 'Setup',
      icon: 'settings',
      children: [
        { label: 'Legal Entity',   icon: 'business',      route: '/setup/legal-entity' },
        { label: 'Processi',       icon: 'account_tree',  route: '/setup/processi' },
        { label: 'Rischi',         icon: 'report_problem',route: '/setup/rischi' },
        { label: 'Controlli',      icon: 'checklist',     route: '/setup/controlli' },
        { label: 'Utenti',         icon: 'group',         route: '/setup/utenti' },
        { label: 'Matrice RCA',    icon: 'table_chart',   route: '/setup/rca' },
      ]
    },
    {
      label: 'Admin',
      icon: 'admin_panel_settings',
      route: '/admin'
    }
  ];

  constructor(private router: Router) {}

  ngOnInit(): void {
    // Traccia la route attiva
    this.activeRoute = this.router.url;
    this.router.events
      .pipe(filter(e => e instanceof NavigationEnd))
      .subscribe((e: any) => {
        this.activeRoute = e.urlAfterRedirects;
        // Chiude drawer mobile alla navigazione
        this.mobileDrawerOpen = false;
      });

    // Espandi di default i sottomenu che contengono la route attiva
    this.navItems.forEach(item => {
      if (item.children) {
        const hasActive = item.children.some(c => this.activeRoute.startsWith(c.route || ''));
        if (hasActive) {
          this.expandedGroups[item.label] = true;
        }
      }
    });

    // Stato iniziale collapse su tablet
    if (window.innerWidth < 1024 && window.innerWidth >= 768) {
      this.collapsed = true;
    }
  }

  // ──────────────────────────────────────────────
  // Toggle sidebar collapse/expand
  // ──────────────────────────────────────────────
  toggleCollapse(): void {
    this.collapsed = !this.collapsed;
  }

  // ──────────────────────────────────────────────
  // Toggle sottomenu
  // ──────────────────────────────────────────────
  toggleGroup(label: string): void {
    this.expandedGroups[label] = !this.expandedGroups[label];
  }

  isGroupExpanded(label: string): boolean {
    return !!this.expandedGroups[label];
  }

  // ──────────────────────────────────────────────
  // Stato attivo
  // ──────────────────────────────────────────────
  isActive(route?: string): boolean {
    if (!route) return false;
    return this.activeRoute === route || this.activeRoute.startsWith(route + '/');
  }

  isGroupActive(item: NavItem): boolean {
    if (!item.children) return false;
    return item.children.some(c => this.isActive(c.route));
  }

  // ──────────────────────────────────────────────
  // Navigazione
  // ──────────────────────────────────────────────
  navigate(route?: string): void {
    if (route) {
      this.router.navigate([route]);
    }
  }

  // ──────────────────────────────────────────────
  // Mobile drawer
  // ──────────────────────────────────────────────
  openMobileDrawer(): void {
    this.mobileDrawerOpen = true;
  }

  closeMobileDrawer(): void {
    this.mobileDrawerOpen = false;
  }

  // ──────────────────────────────────────────────
  // Responsive: chiude drawer se finestra si allarga
  // ──────────────────────────────────────────────
  @HostListener('window:resize', ['$event'])
  onResize(event: Event): void {
    const w = (event.target as Window).innerWidth;
    if (w >= 768) {
      this.mobileDrawerOpen = false;
    }
    if (w >= 1024) {
      // Desktop: rispetta la scelta dell'utente
    } else if (w >= 768) {
      this.collapsed = true;
    }
  }

  // ──────────────────────────────────────────────
  // Logout
  // ──────────────────────────────────────────────
  logout(): void {
    // TODO: chiamare AuthService.logout()
    this.router.navigate(['/login']);
  }

  // ──────────────────────────────────────────────
  // Tooltip testo (per stato collapsed)
  // ──────────────────────────────────────────────
  tooltipText(item: NavItem): string {
    return this.collapsed ? item.label : '';
  }
}
