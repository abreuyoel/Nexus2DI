import { ComponentFixture, TestBed } from '@angular/core/testing';

import { MercChatComponent } from './merc-chat.component';

describe('MercChatComponent', () => {
  let component: MercChatComponent;
  let fixture: ComponentFixture<MercChatComponent>;

  beforeEach(async () => {
    await TestBed.configureTestingModule({
      imports: [MercChatComponent]
    })
    .compileComponents();
    
    fixture = TestBed.createComponent(MercChatComponent);
    component = fixture.componentInstance;
    fixture.detectChanges();
  });

  it('should create', () => {
    expect(component).toBeTruthy();
  });
});
