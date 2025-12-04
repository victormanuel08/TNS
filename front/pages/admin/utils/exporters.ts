// Utilidades para exportar datos

export const exportToCSV = (data: any[], filename: string = 'export.csv') => {
  if (data.length === 0) {
    alert('No hay datos para exportar')
    return
  }

  // Obtener headers de las claves del primer objeto
  const headers = Object.keys(data[0])
  
  // Crear CSV
  let csv = headers.join(',') + '\n'
  
  data.forEach(row => {
    const values = headers.map(header => {
      const value = row[header]
      // Escapar comillas y envolver en comillas si contiene comas
      if (value === null || value === undefined) return ''
      const stringValue = String(value).replace(/"/g, '""')
      return stringValue.includes(',') || stringValue.includes('\n') 
        ? `"${stringValue}"` 
        : stringValue
    })
    csv += values.join(',') + '\n'
  })
  
  // Descargar
  const blob = new Blob([csv], { type: 'text/csv;charset=utf-8;' })
  const link = document.createElement('a')
  const url = URL.createObjectURL(blob)
  link.setAttribute('href', url)
  link.setAttribute('download', filename)
  link.style.visibility = 'hidden'
  document.body.appendChild(link)
  link.click()
  document.body.removeChild(link)
}

export const exportToExcel = async (data: any[], filename: string = 'export.xlsx') => {
  try {
    // Usar una librería como xlsx si está disponible, o generar CSV
    // Por ahora, generamos CSV con extensión .xlsx (Excel puede abrirlo)
    exportToCSV(data, filename.replace('.xlsx', '.csv'))
  } catch (error) {
    console.error('Error exportando a Excel:', error)
    // Fallback a CSV
    exportToCSV(data, filename.replace('.xlsx', '.csv'))
  }
}

export const exportTableToCSV = (tableId: string, filename: string = 'export.csv') => {
  const table = document.getElementById(tableId) as HTMLTableElement
  if (!table) {
    alert('No se encontró la tabla')
    return
  }

  let csv = ''
  const rows = table.querySelectorAll('tr')
  
  rows.forEach(row => {
    const cols = row.querySelectorAll('th, td')
    const rowData: string[] = []
    
    cols.forEach(col => {
      let text = col.textContent || ''
      text = text.replace(/"/g, '""')
      if (text.includes(',') || text.includes('\n')) {
        text = `"${text}"`
      }
      rowData.push(text)
    })
    
    csv += rowData.join(',') + '\n'
  })
  
  // Descargar
  const blob = new Blob([csv], { type: 'text/csv;charset=utf-8;' })
  const link = document.createElement('a')
  const url = URL.createObjectURL(blob)
  link.setAttribute('href', url)
  link.setAttribute('download', filename)
  link.style.visibility = 'hidden'
  document.body.appendChild(link)
  link.click()
  document.body.removeChild(link)
}

