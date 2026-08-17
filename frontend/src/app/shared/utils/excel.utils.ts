import * as XLSX from 'xlsx-js-style';

export interface ParsedTemplateResult {
  idCliente: number;
  items: { id_punto_interes: string; pdv_nombre: string; frecuencia_semanal: number | null; observaciones: string | null }[];
  errors: string[];
}

/**
 * Genera y descarga una plantilla de Excel estilizada y profesional con dos hojas:
 * 1. Frecuencias (con datos de PDVs, columna de filtro por primera palabra y autofiltros)
 * 2. Instrucciones (con reglas y explicaciones estilizadas en azul corporativo)
 */
export function exportFrecuenciaTemplate(clienteNombre: string, clienteId: number, pdvs: any[]): void {
  // --- PALETA DE COLORES Y ESTILOS ---
  const borderStyle = {
    top: { style: 'thin', color: { rgb: 'CBD5E1' } },
    bottom: { style: 'thin', color: { rgb: 'CBD5E1' } },
    left: { style: 'thin', color: { rgb: 'CBD5E1' } },
    right: { style: 'thin', color: { rgb: 'CBD5E1' } }
  };

  // Cabecera Principal (Azul Marino Corporativo)
  const headerStyle = {
    fill: { fgColor: { rgb: '1E3A8A' } }, 
    font: { name: 'Segoe UI', sz: 11, bold: true, color: { rgb: 'FFFFFF' } },
    alignment: { horizontal: 'center', vertical: 'center', wrapText: true },
    border: borderStyle
  };

  // Celdas de Lectura (Gris Claro / Solo lectura)
  const cellReadOnlyLeft = {
    font: { name: 'Segoe UI', sz: 10, color: { rgb: '475569' } },
    fill: { fgColor: { rgb: 'F1F5F9' } },
    alignment: { horizontal: 'left', vertical: 'center' },
    border: borderStyle
  };

  const cellReadOnlyCenter = {
    font: { name: 'Segoe UI', sz: 10, color: { rgb: '475569' } },
    fill: { fgColor: { rgb: 'F1F5F9' } },
    alignment: { horizontal: 'center', vertical: 'center' },
    border: borderStyle
  };

  // Celdas de Escritura - Frecuencia (Verde Claro indicativo de Entrada)
  const cellEditableFreq = {
    font: { name: 'Segoe UI', sz: 10, bold: true, color: { rgb: '14532D' } },
    fill: { fgColor: { rgb: 'DCFCE7' } }, // Verde muy suave
    alignment: { horizontal: 'center', vertical: 'center' },
    border: borderStyle
  };

  // Celdas de Escritura - Observaciones (Blanco estándar / editable)
  const cellEditableObs = {
    font: { name: 'Segoe UI', sz: 10, color: { rgb: '000000' } },
    fill: { fgColor: { rgb: 'FFFFFF' } },
    alignment: { horizontal: 'left', vertical: 'center' },
    border: borderStyle
  };

  // Estilos de Metadatos (Filas de arriba)
  const metadataLabelStyle = {
    font: { name: 'Segoe UI', sz: 10, bold: true, color: { rgb: '334155' } },
    fill: { fgColor: { rgb: 'F8FAFC' } },
    alignment: { horizontal: 'left', vertical: 'center' }
  };

  const metadataValueStyle = {
    font: { name: 'Segoe UI', sz: 10, bold: true, color: { rgb: '0F172A' } },
    fill: { fgColor: { rgb: 'F8FAFC' } },
    alignment: { horizontal: 'left', vertical: 'center' }
  };

  // --- CONSTRUCCIÓN HOJA 1: FRECUENCIAS ---
  const rows: any[] = [];

  // Títulos
  rows.push([
    {
      v: "NEXUS 2DI - SISTEMA DE GESTIÓN OPERATIVA",
      t: 's',
      s: {
        font: { name: 'Segoe UI', sz: 14, bold: true, color: { rgb: '1E3A8A' } },
        alignment: { horizontal: 'left', vertical: 'center' }
      }
    }
  ]);
  rows.push([
    {
      v: "PLANTILLA OFICIAL DE CARGA MASIVA DE FRECUENCIAS",
      t: 's',
      s: {
        font: { name: 'Segoe UI', sz: 11, bold: true, color: { rgb: '475569' } },
        alignment: { horizontal: 'left', vertical: 'center' }
      }
    }
  ]);
  rows.push([
    {
      v: "------------------------------------------------------------------------------------------------",
      t: 's',
      s: { font: { name: 'Segoe UI', sz: 9, color: { rgb: 'CBD5E1' } } }
    }
  ]);

  // Metadatos
  rows.push([
    { v: "CLIENTE DESTINO:", t: 's', s: metadataLabelStyle },
    { v: clienteNombre.toUpperCase(), t: 's', s: metadataValueStyle }
  ]);
  rows.push([
    { v: "ID CLIENTE (NO MODIFICAR):", t: 's', s: metadataLabelStyle },
    { v: clienteId, t: 'n', s: metadataValueStyle }
  ]);
  rows.push([
    { v: "FECHA GENERACIÓN:", t: 's', s: metadataLabelStyle },
    { v: new Date().toLocaleDateString(), t: 's', s: metadataValueStyle }
  ]);
  rows.push([
    {
      v: "------------------------------------------------------------------------------------------------",
      t: 's',
      s: { font: { name: 'Segoe UI', sz: 9, color: { rgb: 'CBD5E1' } } }
    }
  ]);
  rows.push([]); // Espacio

  // Cabecera Tabla (5 columnas ahora)
  rows.push([
    { v: "ID PDV (NO MODIFICAR)", t: 's', s: headerStyle },
    { v: "NOMBRE PDV (NO MODIFICAR)", t: 's', s: headerStyle },
    { v: "FILTRO PDV (PRIMERA PALABRA)", t: 's', s: headerStyle }, // Nueva columna de filtro rápido
    { v: "FRECUENCIA SEMANAL (EDITABLE - VERDE)", t: 's', s: headerStyle },
    { v: "OBSERVACIONES (EDITABLE - BLANCO)", t: 's', s: headerStyle }
  ]);

  // Carga de PDVs
  for (const pdv of pdvs) {
    const pdvName = pdv.pdv_nombre || '';
    // Obtener la primera palabra para el filtro rápido
    const firstWord = pdvName.trim().split(/\s+/)[0] || '';
    
    rows.push([
      { v: pdv.id_punto_interes || '', t: 's', s: cellReadOnlyCenter },
      { v: pdvName, t: 's', s: cellReadOnlyLeft },
      { v: firstWord, t: 's', s: cellReadOnlyCenter }, // Columna C: Filtro primera palabra
      {
        v: pdv.frecuencia_semanal !== null && pdv.frecuencia_semanal !== undefined ? pdv.frecuencia_semanal : '',
        t: pdv.frecuencia_semanal !== null && pdv.frecuencia_semanal !== undefined ? 'n' : 's',
        s: cellEditableFreq
      },
      { v: pdv.observaciones || '', t: 's', s: cellEditableObs }
    ]);
  }

  const ws = XLSX.utils.aoa_to_sheet(rows);

  // Asegurar líneas de cuadrícula visibles
  ws['!views'] = [{ showGridLines: true }];

  // Ajustar anchos (5 columnas)
  ws['!cols'] = [
    { wch: 25 }, // ID PDV
    { wch: 45 }, // Nombre PDV
    { wch: 30 }, // Filtro PDV (Primera Palabra)
    { wch: 40 }, // Frecuencia Semanal
    { wch: 45 }  // Observaciones
  ];

  // Auto-filtros nativos en cabeceras de tabla (A9 a E[last])
  const lastRow = rows.length;
  if (lastRow >= 9) {
    ws['!autofilter'] = { ref: `A9:E${lastRow}` };
  }

  // --- CONSTRUCCIÓN HOJA 2: INSTRUCCIONES ---
  const instRows: any[] = [];
  
  instRows.push([
    {
      v: "NEXUS 2DI - GUÍA DE INSTRUCCIONES DE CARGA",
      t: 's',
      s: {
        font: { name: 'Segoe UI', sz: 14, bold: true, color: { rgb: '1E3A8A' } },
        alignment: { horizontal: 'left', vertical: 'center' }
      }
    }
  ]);
  instRows.push([
    {
      v: "INDICACIONES DE USO PARA EVITAR ERRORES DE FORMATO",
      t: 's',
      s: {
        font: { name: 'Segoe UI', sz: 11, bold: true, color: { rgb: '475569' } },
        alignment: { horizontal: 'left', vertical: 'center' }
      }
    }
  ]);
  instRows.push([]);

  // Cabecera tabla de instrucciones
  instRows.push([
    { v: "Concepto / Regla", t: 's', s: headerStyle },
    { v: "Instrucciones de Llenado", t: 's', s: headerStyle }
  ]);

  const rules = [
    ["1. Áreas de Solo Lectura (Gris)", "Las columnas 'ID PDV', 'Nombre PDV' y 'Filtro PDV' tienen fondo GRIS. Por favor, no las modifique, ya que identifican el local de forma única."],
    ["2. Columna Filtro Rápido", "La columna 'Filtro PDV (Primera Palabra)' extrae automáticamente la primera palabra del nombre (ej: Oxxo, Farmacia, Exito). Puede hacer clic en el desplegable de filtro de esta columna en Excel para agrupar y visualizar rápidamente solo los locales de esa cadena."],
    ["3. Carga de Frecuencias (Verde)", "La columna de frecuencias tiene fondo VERDE para indicar que es un campo de ENTRADA. Ingrese EXCLUSIVAMENTE valores numéricos (ej: 1, 3, 5, 0.5)."],
    ["4. Prohibido incluir Texto", "No escriba letras ni unidades como 'veces', 'visitas' o 'días' en la columna de frecuencias. Solo coloque el número puro."],
    ["5. Formato Decimal", "Puede utilizar tanto comas (0,5) como puntos (0.5) para indicar decimales. Ambos formatos son aceptados por el cargador."],
    ["6. Comentarios (Blanco)", "La columna de observaciones es libre para texto opcional y tiene fondo BLANCO."],
    ["7. Preservar Cabeceras", "No altere las primeras 8 filas del Excel (ID Cliente, Cliente, etc.). Son requeridas por motivos de seguridad."]
  ];

  for (const r of rules) {
    instRows.push([
      { v: r[0], t: 's', s: { font: { name: 'Segoe UI', sz: 10, bold: true, color: { rgb: '1E3A8A' } }, border: borderStyle, fill: { fgColor: { rgb: 'F8FAFC' } } } },
      { v: r[1], t: 's', s: { font: { name: 'Segoe UI', sz: 10 }, border: borderStyle } }
    ]);
  }

  instRows.push([]);
  instRows.push([
    {
      v: "TABLA DE REFERENCIA DE VALORES:",
      t: 's',
      s: { font: { name: 'Segoe UI', sz: 11, bold: true, color: { rgb: '1E3A8A' } } }
    }
  ]);

  instRows.push([
    { v: "Frecuencia (Dato Numérico)", t: 's', s: headerStyle },
    { v: "Significado Real", t: 's', s: headerStyle }
  ]);

  const freqs = [
    [5, "Visitar 5 días a la semana"],
    [3, "Visitar 3 días a la semana"],
    [1, "Visitar 1 vez a la semana (4 visitas al mes)"],
    [0.5, "Visitar quincenalmente (2 visitas al mes)"],
    [0.25, "Visitar mensualmente (1 visita al mes)"]
  ];

  for (const f of freqs) {
    instRows.push([
      { v: f[0], t: 'n', s: { font: { name: 'Segoe UI', sz: 10, bold: true, color: { rgb: '14532D' } }, fill: { fgColor: { rgb: 'DCFCE7' } }, border: borderStyle, alignment: { horizontal: 'center' } } },
      { v: f[1], t: 's', s: { font: { name: 'Segoe UI', sz: 10 }, border: borderStyle } }
    ]);
  }

  const wsInst = XLSX.utils.aoa_to_sheet(instRows);
  
  wsInst['!views'] = [{ showGridLines: true }];
  wsInst['!cols'] = [
    { wch: 30 },
    { wch: 100 }
  ];

  const wb = XLSX.utils.book_new();
  XLSX.utils.book_append_sheet(wb, ws, "Frecuencias");
  XLSX.utils.book_append_sheet(wb, wsInst, "Instrucciones");

  const cleanClientName = clienteNombre.replace(/[^a-zA-Z0-9]/g, '_');
  const dateStr = new Date().toISOString().slice(0, 10);
  XLSX.writeFile(wb, `Plantilla_Frecuencias_${cleanClientName}_${dateStr}.xlsx`);
}

/**
 * Lee un archivo de Excel cargado y valida su estructura y tipo de datos.
 */
export function parseFrecuenciaTemplate(file: File): Promise<ParsedTemplateResult> {
  return new Promise((resolve, reject) => {
    const reader = new FileReader();
    reader.onload = (e: any) => {
      try {
        const data = new Uint8Array(e.target.result);
        const workbook = XLSX.read(data, { type: 'array' });

        const sheetName = workbook.SheetNames.find(name => name.toLowerCase() === 'frecuencias');
        if (!sheetName) {
          resolve({
            idCliente: 0,
            items: [],
            errors: ["No se encontró la pestaña 'Frecuencias' en el archivo Excel. Asegúrese de usar la plantilla original."]
          });
          return;
        }

        const ws = workbook.Sheets[sheetName];

        // Celda B5 (Fila 5, Columna 2) -> ID Cliente
        const cellB5 = ws['B5'];
        const idClienteRaw = cellB5 ? cellB5.v : null;
        const idCliente = idClienteRaw ? Number(idClienteRaw) : 0;

        if (!idCliente || isNaN(idCliente)) {
          resolve({
            idCliente: 0,
            items: [],
            errors: ["No se pudo leer el ID del Cliente en la celda B5 de la hoja 'Frecuencias'. Asegúrese de no modificar las cabeceras."]
          });
          return;
        }

        const rawRows: any[] = XLSX.utils.sheet_to_json(ws, { header: 1, defval: '' });

        // Las cabeceras están en el índice 8 (Fila 9). Los datos reales inician en índice 9 (Fila 10)
        if (rawRows.length <= 9) {
          resolve({
            idCliente,
            items: [],
            errors: ["El archivo no contiene filas de datos de locales (PDVs) para procesar."]
          });
          return;
        }

        const items: any[] = [];
        const errors: string[] = [];

        for (let i = 9; i < rawRows.length; i++) {
          const row = rawRows[i];
          if (!row || row.length === 0) continue;

          const idPdv = String(row[0] || '').trim();
          const pdvNombre = String(row[1] || '').trim();
          // row[2] es la columna 'Filtro PDV (Primera Palabra)'
          const freqRaw = row[3]; // Ahora en índice 3
          const obsRaw = row[4];  // Ahora en índice 4

          if (!idPdv && !pdvNombre && freqRaw === '' && obsRaw === '') continue;

          if (!idPdv) {
            errors.push(`Fila ${i + 1}: El código de identificación (ID PDV) está vacío.`);
            continue;
          }

          let freqVal: number | null = null;
          if (freqRaw !== undefined && freqRaw !== null && String(freqRaw).trim() !== '') {
            const freqStr = String(freqRaw).trim().replace(',', '.');
            const parsed = Number(freqStr);
            if (isNaN(parsed)) {
              errors.push(`Fila ${i + 1} (${pdvNombre || idPdv}): La frecuencia '${freqRaw}' debe ser un dato puramente numérico (ej. 1, 0.5).`);
            } else {
              freqVal = parsed;
            }
          }

          items.push({
            id_punto_interes: idPdv,
            pdv_nombre: pdvNombre,
            frecuencia_semanal: freqVal,
            observaciones: obsRaw !== undefined && obsRaw !== null ? String(obsRaw).trim() : null
          });
        }

        resolve({
          idCliente,
          items,
          errors
        });
      } catch (err) {
        reject(err);
      }
    };
    reader.onerror = (err) => reject(err);
    reader.readAsArrayBuffer(file);
  });
}
