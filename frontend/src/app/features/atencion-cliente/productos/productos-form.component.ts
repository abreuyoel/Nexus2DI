import { Component, Inject } from '@angular/core';
import { CommonModule } from '@angular/common';
import { FormsModule, ReactiveFormsModule, FormBuilder, Validators, FormGroup } from '@angular/forms';
import { MatDialogModule, MAT_DIALOG_DATA, MatDialogRef } from '@angular/material/dialog';
import { MatFormFieldModule } from '@angular/material/form-field';
import { MatInputModule } from '@angular/material/input';
import { MatSelectModule } from '@angular/material/select';
import { MatButtonModule } from '@angular/material/button';
import { MatCheckboxModule } from '@angular/material/checkbox';
import { MatIconModule } from '@angular/material/icon';

export interface DialogData {
  producto: any | null;
  categorias: string[];
  fabricantes: string[];
  tiposServicio: string[];
  tiposFabricante: string[];
}

@Component({
  selector: 'app-productos-form',
  standalone: true,
  imports: [
    CommonModule,
    FormsModule,
    ReactiveFormsModule,
    MatDialogModule,
    MatFormFieldModule,
    MatInputModule,
    MatSelectModule,
    MatButtonModule,
    MatCheckboxModule,
    MatIconModule,
  ],
  template: `
    <div>
      <!-- Header -->
      <h2 mat-dialog-title class="mb-4">
        {{ data.producto ? 'Editar Producto' : 'Nuevo Producto' }}
      </h2>

      <!-- Form -->
      <form [formGroup]="formulario" (ngSubmit)="onSubmit()" class="space-y-4">
        <!-- SKU (Nombre) - Requerido -->
        <mat-form-field class="w-full">
          <mat-label>SKU (Nombre del Producto)*</mat-label>
          <input matInput formControlName="SKUs" placeholder="Ej: SKU001" />
          <mat-error *ngIf="formulario.get('SKUs')?.hasError('required')">
            SKU es requerido
          </mat-error>
        </mat-form-field>

        <!-- Categoría -->
        <mat-form-field class="w-full">
          <mat-label>Categoría</mat-label>
          <mat-select formControlName="categoria">
            <mat-option value="">-- Sin categoría --</mat-option>
            <mat-option *ngFor="let cat of data.categorias" [value]="cat">
              {{ cat }}
            </mat-option>
          </mat-select>
        </mat-form-field>

        <!-- Fabricante -->
        <mat-form-field class="w-full">
          <mat-label>Fabricante</mat-label>
          <mat-select formControlName="fabricante">
            <mat-option value="">-- Sin fabricante --</mat-option>
            <mat-option *ngFor="let fab of data.fabricantes" [value]="fab">
              {{ fab }}
            </mat-option>
          </mat-select>
        </mat-form-field>

        <!-- Tipo de Servicio -->
        <mat-form-field class="w-full">
          <mat-label>Tipo de Servicio</mat-label>
          <mat-select formControlName="tipo_servicio">
            <mat-option value="">-- Sin tipo --</mat-option>
            <mat-option *ngFor="let tipo of data.tiposServicio" [value]="tipo">
              {{ tipo }}
            </mat-option>
          </mat-select>
        </mat-form-field>

        <!-- Tipo de Fabricante -->
        <mat-form-field class="w-full">
          <mat-label>Tipo de Fabricante</mat-label>
          <mat-select formControlName="tipo_fabricante">
            <mat-option value="">-- Sin tipo --</mat-option>
            <mat-option *ngFor="let tipo of data.tiposFabricante" [value]="tipo">
              {{ tipo }}
            </mat-option>
          </mat-select>
        </mat-form-field>

        <!-- Código de Barras -->
        <mat-form-field class="w-full">
          <mat-label>Código de Barras</mat-label>
          <input matInput formControlName="cod_bar" placeholder="Ej: 7501234567890" />
        </mat-form-field>

        <!-- ID Fabricante -->
        <mat-form-field class="w-full">
          <mat-label>ID Fabricante</mat-label>
          <input matInput type="number" formControlName="id_fabricante" />
        </mat-form-field>

        <!-- ID Categoría -->
        <mat-form-field class="w-full">
          <mat-label>ID Categoría</mat-label>
          <input matInput type="number" formControlName="id_categoria" />
        </mat-form-field>

        <!-- Inagotable -->
        <div class="flex items-center mt-4">
          <mat-checkbox formControlName="inagotable" class="mr-2">
            Producto Inagotable
          </mat-checkbox>
          <span class="text-gray-600 text-sm">
            Marcar si el producto no se agota en inventario
          </span>
        </div>

        <!-- Botones -->
        <div class="flex justify-end gap-2 mt-6">
          <button type="button" mat-stroked-button (click)="onCancel()">
            Cancelar
          </button>
          <button
            type="submit"
            mat-raised-button
            color="primary"
            [disabled]="formulario.invalid"
          >
            {{ data.producto ? 'Actualizar' : 'Guardar' }}
          </button>
        </div>
      </form>
    </div>
  `,
  styles: [
    `
      .w-full {
        width: 100%;
      }

      .space-y-4 > * + * {
        margin-top: 1rem;
      }

      .flex {
        display: flex;
      }

      .items-center {
        align-items: center;
      }

      .gap-2 {
        gap: 0.5rem;
      }

      .justify-end {
        justify-content: flex-end;
      }

      .mt-4 {
        margin-top: 1rem;
      }

      .mt-6 {
        margin-top: 1.5rem;
      }

      .mb-4 {
        margin-bottom: 1rem;
      }

      .mr-2 {
        margin-right: 0.5rem;
      }

      .text-gray-600 {
        color: #4b5563;
      }

      .text-sm {
        font-size: 0.875rem;
      }
    `,
  ],
})
export class ProductosFormComponent {
  formulario: FormGroup;

  constructor(
    private fb: FormBuilder,
    public dialogRef: MatDialogRef<ProductosFormComponent>,
    @Inject(MAT_DIALOG_DATA) public data: DialogData
  ) {
    this.formulario = this.fb.group({
      SKUs: ['', Validators.required],
      categoria: [''],
      fabricante: [''],
      tipo_servicio: [''],
      tipo_fabricante: [''],
      cod_bar: [''],
      id_fabricante: [''],
      id_categoria: [''],
      inagotable: [false],
    });

    // Si es edición, llenar el formulario con datos existentes
    if (data.producto) {
      this.formulario.patchValue({
        SKUs: data.producto.SKUs || '',
        categoria: data.producto.categoria || '',
        fabricante: data.producto.fabricante || '',
        tipo_servicio: data.producto.tipo_servicio || '',
        tipo_fabricante: data.producto.tipo_fabricante || '',
        cod_bar: data.producto.cod_bar || '',
        id_fabricante: data.producto.id_fabricante || '',
        id_categoria: data.producto.id_categoria || '',
        inagotable: data.producto.inagotable || false,
      });
    }
  }

  /**
   * Enviar formulario
   */
  onSubmit(): void {
    if (this.formulario.valid) {
      this.dialogRef.close(this.formulario.value);
    }
  }

  /**
   * Cancelar y cerrar diálogo
   */
  onCancel(): void {
    this.dialogRef.close(null);
  }
}
