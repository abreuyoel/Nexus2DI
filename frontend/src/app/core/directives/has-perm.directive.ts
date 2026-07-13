import { Directive, Input, TemplateRef, ViewContainerRef, inject } from '@angular/core';
import { AuthService } from '../services/auth.service';

/**
 * Estructural: muestra el elemento solo si el usuario tiene el permiso indicado.
 *   <button *hasPerm="'products.crear'">…</button>            (acción → 'read')
 *   <div    *hasPerm="'products'; action:'write'">…</div>      (módulo → write)
 * Admin siempre ve. Si la clave no está permitida, el elemento no se renderiza.
 */
@Directive({ selector: '[hasPerm]', standalone: true })
export class HasPermDirective {
  private tpl = inject(TemplateRef<any>);
  private vcr = inject(ViewContainerRef);
  private auth = inject(AuthService);
  private shown = false;
  private key = '';
  private act: 'read' | 'write' | 'delete' = 'read';

  @Input() set hasPerm(clave: string) { this.key = clave; this.update(); }
  @Input() set hasPermAction(a: 'read' | 'write' | 'delete') { this.act = a || 'read'; this.update(); }

  private update() {
    if (!this.key) return;
    const ok = this.auth.can(this.key, this.act);
    if (ok && !this.shown) { this.vcr.createEmbeddedView(this.tpl); this.shown = true; }
    else if (!ok && this.shown) { this.vcr.clear(); this.shown = false; }
  }
}
