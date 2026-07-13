import { ComponentFixture, TestBed } from '@angular/core/testing';

import { MercPerfilComponent } from './merc-perfil.component';

describe('MercPerfilComponent', () => {
  let component: MercPerfilComponent;
  let fixture: ComponentFixture<MercPerfilComponent>;

  beforeEach(async () => {
    await TestBed.configureTestingModule({
      imports: [MercPerfilComponent]
    })
    .compileComponents();
    
    fixture = TestBed.createComponent(MercPerfilComponent);
    component = fixture.componentInstance;
    fixture.detectChanges();
  });

  it('should create', () => {
    expect(component).toBeTruthy();
  });
});
