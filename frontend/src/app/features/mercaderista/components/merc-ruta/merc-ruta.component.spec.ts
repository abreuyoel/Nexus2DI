import { ComponentFixture, TestBed } from '@angular/core/testing';

import { MercRutaComponent } from './merc-ruta.component';

describe('MercRutaComponent', () => {
  let component: MercRutaComponent;
  let fixture: ComponentFixture<MercRutaComponent>;

  beforeEach(async () => {
    await TestBed.configureTestingModule({
      imports: [MercRutaComponent]
    })
    .compileComponents();
    
    fixture = TestBed.createComponent(MercRutaComponent);
    component = fixture.componentInstance;
    fixture.detectChanges();
  });

  it('should create', () => {
    expect(component).toBeTruthy();
  });
});
