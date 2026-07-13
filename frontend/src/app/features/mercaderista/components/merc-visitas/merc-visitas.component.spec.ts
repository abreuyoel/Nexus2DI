import { ComponentFixture, TestBed } from '@angular/core/testing';

import { MercVisitasComponent } from './merc-visitas.component';

describe('MercVisitasComponent', () => {
  let component: MercVisitasComponent;
  let fixture: ComponentFixture<MercVisitasComponent>;

  beforeEach(async () => {
    await TestBed.configureTestingModule({
      imports: [MercVisitasComponent]
    })
    .compileComponents();
    
    fixture = TestBed.createComponent(MercVisitasComponent);
    component = fixture.componentInstance;
    fixture.detectChanges();
  });

  it('should create', () => {
    expect(component).toBeTruthy();
  });
});
