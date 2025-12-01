<template>
  <div class="autopago-container">
    <!-- Debug Banner: Mostrar solo cuando es ADMIN -->
    <div v-if="isAdmin" class="debug-banner admin-mode" :style="{ backgroundColor: currentBranding?.color_primario || '#DC2626' }">
      🔧 MODO ADMIN ACTIVO - Username: {{ session.tnsUsername.value || 'No detectado' }}
    </div>
    
    
    <!-- Modal: Cambiar de usuario (Login/Logout) -->
    <div v-if="showUserSwitchModal" class="modal-overlay" @click.self="cancelUserSwitch">
      <div class="modal-content invoice-modal" @click.stop>
        <!-- Si es Admin, mostrar opción de volver a CAJAGC -->
        <div v-if="isAdmin">
          <h2 class="modal-title">Volver a CAJAGC</h2>
          <div class="invoice-form">
            <div class="form-group">
              <p class="switch-message">¿Volver a modo CAJAGC?</p>
            </div>
            <div class="button-group">
              <button 
                @click="switchToCajagc" 
                class="continue-btn"
                :disabled="switchingUser"
              >
                <span v-if="switchingUser" class="spinner-small"></span>
                <span v-else>Volver a CAJAGC</span>
              </button>
              <button 
                @click="cancelUserSwitch" 
                class="back-btn"
                :disabled="switchingUser"
              >
                Cancelar
              </button>
            </div>
          </div>
        </div>
        
        <!-- Si es CAJAGC, mostrar formulario de login (igual que teléfono) -->
        <div v-else>
          <h2 class="modal-title">Contraseña de Admin</h2>
          <div class="invoice-form">
            <div class="form-group">
              <label>Ingresa la contraseña: <span class="required">*</span></label>
              <!-- Display centrado mostrando asteriscos (más pequeño que teléfono) -->
              <div 
                class="password-display"
                :class="{ 'has-value': userSwitchForm.password && userSwitchForm.password.trim() !== '' }"
                @click="() => { if (typeof document !== 'undefined') { const input = document.querySelector('.password-input-hidden') as HTMLInputElement; if (input) input.focus() } }"
              >
                {{ userSwitchForm.password ? '*'.repeat(userSwitchForm.password.length) : '---' }}
              </div>
              <!-- Input oculto para capturar teclado -->
              <input 
                v-model="userSwitchForm.password" 
                type="password" 
                class="form-input password-input-hidden"
                :inputmode="shouldUseVirtualKeyboard('text') ? 'none' : 'text'"
                :pattern="shouldUseVirtualKeyboard('text') ? undefined : '.*'"
                :readonly="shouldUseVirtualKeyboard('text')"
                placeholder=""
                ref="passwordInputAdmin"
                @focus="(e) => { const target = e.target as HTMLInputElement; if (target && shouldUseVirtualKeyboard('text')) { setTimeout(() => openVirtualKeyboard(target, 'text'), 100) } }"
                @keyup.enter="handleUserSwitchLogin"
                @keyup.delete="userSwitchForm.password = ''"
                @keyup.backspace="userSwitchForm.password = ''"
                required
                autofocus
                :disabled="switchingUser"
              />
            </div>
            <p v-if="userSwitchError" class="error-message">{{ userSwitchError }}</p>
            <div class="button-group">
              <button 
                @click="handleUserSwitchLogin" 
                class="continue-btn"
                :disabled="switchingUser || !userSwitchForm.password"
              >
                <span v-if="switchingUser" class="spinner-small"></span>
                <span v-else>Cambiar a Admin</span>
              </button>
              <button 
                @click="cancelUserSwitch" 
                class="back-btn"
                :disabled="switchingUser"
              >
                Cancelar
              </button>
            </div>
          </div>
        </div>
      </div>
    </div>
    
    <!-- Modal: PDF de Factura -->
    <div v-if="showInvoicePdfModal" class="modal-overlay invoice-pdf-modal-overlay">
      <div class="modal-content invoice-pdf-modal">
        <!-- Header con botón de imprimir -->
        <div class="invoice-pdf-header">
          <h2 class="modal-title">Factura Generada</h2>
          <div class="header-actions">
            <button 
              @click="imprimirPdfActual" 
              class="btn-print-header"
              :disabled="(pdfTabActiva === 'corto' && !ticketCortoBlob) || (pdfTabActiva === 'completo' && (!pdfCompletoDisponible || !pdfCompletoBlob))"
              title="Imprimir"
            >
              <svg class="btn-icon" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                <path d="M6 9V2h12v7M6 18H4a2 2 0 0 1-2-2v-5a2 2 0 0 1 2-2h16a2 2 0 0 1 2 2v5a2 2 0 0 1-2 2h-2"/>
                <path d="M6 14h12v8H6z"/>
              </svg>
              <span class="btn-text">Imprimir</span>
            </button>
          </div>
        </div>
        
        <!-- Pestañas debajo del header -->
        <div class="pdf-tabs" v-if="ticketPdfUrl || invoicePdfUrl">
          <button 
            @click="pdfTabActiva = 'corto'"
            :class="['pdf-tab', { active: pdfTabActiva === 'corto' }]"
            :disabled="!ticketPdfUrl"
          >
            🎫 Ticket
          </button>
          <button 
            @click="pdfTabActiva = 'completo'"
            :class="['pdf-tab', { active: pdfTabActiva === 'completo', disabled: !pdfCompletoDisponible }]"
            :disabled="!pdfCompletoDisponible"
          >
            📄 Factura Completa
            <span v-if="!pdfCompletoDisponible" class="badge">Generando...</span>
          </button>
        </div>
        
        <div class="invoice-pdf-content">
          <div v-if="isGeneratingPdf && !ticketPdfUrl && !invoicePdfUrl" class="pdf-loading">
            <div class="spinner"></div>
            <p>Generando PDF...</p>
          </div>
          
          <div v-else-if="pdfTabActiva === 'corto' && ticketPdfUrl" class="pdf-preview">
            <iframe 
              :src="ticketPdfUrl + '#toolbar=0&navpanes=0&scrollbar=0'" 
              class="pdf-iframe"
              frameborder="0"
            ></iframe>
          </div>
          
          <div v-else-if="pdfTabActiva === 'completo' && invoicePdfUrl" class="pdf-preview">
            <iframe 
              :src="invoicePdfUrl + '#toolbar=0&navpanes=0&scrollbar=0'" 
              class="pdf-iframe"
              frameborder="0"
            ></iframe>
          </div>
          
          <div v-else-if="pdfTabActiva === 'completo' && !pdfCompletoDisponible" class="pdf-loading">
            <div class="spinner"></div>
            <p>Generando factura completa con CUFE de DIAN...</p>
          </div>
          
          <div v-else class="pdf-placeholder">
            <div class="pdf-icon">📄</div>
            <p>Generando PDFs...</p>
          </div>
        </div>
      </div>
    </div>

    <!-- Modal: Para llevar o comer aquí -->
    <!-- Modal: Tipo de pedido (Para Llevar / Para Comer Aquí) - Solo para modo comida -->
    <div v-if="showOrderTypeModal && esModoComida" class="modal-overlay">
      <div class="modal-content" @click.stop>
        <h2 class="modal-title">¿Cómo deseas tu pedido?</h2>
        <div class="modal-options">
          <button class="option-btn" @click="selectOrderType('takeaway')">
            <span class="option-icon">🥡</span>
            <span class="option-label">Para Llevar</span>
          </button>
          <button class="option-btn" @click="selectOrderType('dinein')">
            <span class="option-icon">🍽️</span>
            <span class="option-label">Para Comer Aquí</span>
          </button>
        </div>
        <!-- Mostrar mesa si ya está seleccionada -->
        <div v-if="orderType === 'dinein' && mesaNumber" class="mesa-display-inline">
          <p>Mesa: <strong>{{ mesaNumber }}</strong></p>
          <button @click="showMesaModal = true" class="change-mesa-btn">Cambiar Mesa</button>
        </div>
      </div>
    </div>

    <!-- Modal: Número de mesa (solo si es para comer aquí) -->
    <div v-if="showMesaModal" class="modal-overlay" @click.self="showMesaModal = false">
      <div class="modal-content invoice-modal">
        <h2 class="modal-title">Número de Mesa</h2>
        <div class="invoice-form">
          <div class="form-group">
            <label>Ingresa el número de mesa:</label>
            <!-- Label grande centrado mostrando números digitados -->
            <div 
              class="mesa-display"
              :class="{ 'has-value': mesaNumber && mesaNumber.trim() !== '' }"
              @click="() => { if (typeof document !== 'undefined') { const input = document.querySelector('.mesa-input-hidden') as HTMLInputElement; if (input) input.focus() } }"
            >
              {{ mesaNumber || '---' }}
            </div>
            <!-- Input oculto para capturar teclado -->
            <input 
              v-model="mesaNumber" 
              type="text" 
              :inputmode="shouldUseVirtualKeyboard('numeric') ? 'none' : 'numeric'"
              :pattern="shouldUseVirtualKeyboard('numeric') ? undefined : '[0-9]*'"
              :readonly="shouldUseVirtualKeyboard('numeric')"
              placeholder=""
              class="form-input mesa-input-hidden"
              @focus="(e) => { const target = e.target as HTMLInputElement; if (target && shouldUseVirtualKeyboard('numeric')) { setTimeout(() => openVirtualKeyboard(target, 'numeric'), 100) } }"
              @keyup.enter="confirmMesa"
              @keyup.delete="mesaNumber = ''"
              @keyup.backspace="mesaNumber = ''"
              autofocus
            />
          </div>
          <div class="button-group">
            <button 
              class="continue-btn" 
              @click="confirmMesa"
            >
              Continuar
            </button>
            <button 
              class="continue-btn" 
              @click="selectSinMesa"
              style="background: #666;"
            >
              Sin Mesa
            </button>
            <button class="back-btn" @click="cancelMesaModal">
              ← Atrás
            </button>
          </div>
        </div>
      </div>
    </div>

    <!-- Modal 1: ¿Deseas factura electrónica a nombre propio o consumidor final? (PRIMER PASO) -->
    <div v-if="showInvoiceModal" class="modal-overlay">
      <div class="modal-content">
        <h2 class="modal-title">¿Deseas factura electrónica a nombre propio o consumidor final?</h2>
        
        <div class="modal-options">
          <button 
            class="option-btn" 
            :class="{ active: wantsInvoice === 'propio' }"
            @click="selectInvoiceType('propio')"
          >
            <span class="option-icon">✅</span>
            <span class="option-label">A Nombre Propio</span>
          </button>
          <button 
            class="option-btn" 
            :class="{ active: wantsInvoice === 'consumidor' }"
            @click="selectInvoiceType('consumidor')"
          >
            <span class="option-icon">👤</span>
            <span class="option-label">Consumidor Final</span>
          </button>
        </div>
        
        <button class="cancel-btn" @click="cancelInvoiceModal">
          Cancelar
        </button>
      </div>
    </div>

    <!-- Modal 2: Tipo documento y número (SI ES A NOMBRE PROPIO) -->
    <div v-if="showDocumentModal" class="modal-overlay">
      <div class="modal-content invoice-modal">
        <h2 class="modal-title">Ingresa tu Documento</h2>
        
        <div class="invoice-form">
          <div class="form-group">
            <label>Tipo de Documento:</label>
            <div class="radio-group">
              <label class="radio-label">
                <input type="radio" v-model="invoiceData.docType" value="cedula" />
                Cédula
              </label>
              <label class="radio-label">
                <input type="radio" v-model="invoiceData.docType" value="nit" />
                NIT
              </label>
            </div>
          </div>

          <div class="form-group">
            <label v-if="invoiceData.docType === 'cedula'">Número de Cédula:</label>
            <label v-else>NIT:</label>
            <input 
              v-model="invoiceData.document" 
              type="text" 
              :inputmode="shouldUseVirtualKeyboard('numeric') ? 'none' : 'numeric'"
              :pattern="shouldUseVirtualKeyboard('numeric') ? undefined : '[0-9]*'"
              :readonly="shouldUseVirtualKeyboard('numeric')"
              :placeholder="invoiceData.docType === 'cedula' ? 'Ej: 1234567890' : 'Ej: 900123456-1'"
              class="form-input"
              @focus="(e) => { const target = e.target as HTMLInputElement; if (target && shouldUseVirtualKeyboard('numeric')) openVirtualKeyboard(target, 'numeric') }"
              @keyup.enter="validateDocument"
            />
          </div>

          <div v-if="isValidatingDocument" class="validating-message">
            <div class="spinner-small"></div>
            <p>Validando documento...</p>
          </div>

          <div class="button-group">
            <button 
              class="continue-btn" 
              @click="validateDocument"
              :disabled="!invoiceData.document || invoiceData.document.length < 7 || isValidatingDocument"
            >
              {{ isValidatingDocument ? 'Validando...' : 'Validar y Continuar' }}
            </button>
            <button class="cancel-btn" @click="cancelDocumentModal">
              Cancelar
            </button>
          </div>
        </div>
      </div>
    </div>

    <!-- Modal 3: Formulario completo de factura (DESPUÉS DE VALIDAR DOCUMENTO) -->
    <div v-if="showCompleteDataModal" class="modal-overlay">
      <div class="modal-content invoice-modal">
        <h2 class="modal-title">Completa los Datos de Facturación</h2>
        
        <div class="invoice-form">
          <div v-if="validatedData.name" class="info-message">
            ✅ Datos encontrados: {{ validatedData.name }}
          </div>

          <div class="form-group">
            <label>Naturaleza:</label>
            <div class="radio-group">
              <label class="radio-label">
                <input type="radio" v-model="invoiceData.nature" value="natural" />
                Natural
              </label>
              <label class="radio-label">
                <input type="radio" v-model="invoiceData.nature" value="juridica" />
                Jurídica
              </label>
            </div>
          </div>

          <div class="form-group">
            <label v-if="invoiceData.nature === 'natural'">Nombre Completo: <span class="required">*</span></label>
            <label v-else>Razón Social: <span class="required">*</span></label>
            <input 
              v-model="invoiceData.name" 
              type="text" 
              :inputmode="shouldUseVirtualKeyboard('text') ? 'none' : 'text'"
              :readonly="shouldUseVirtualKeyboard('text')"
              :placeholder="invoiceData.nature === 'natural' ? 'Nombre y Apellidos' : 'Razón Social de la Empresa'"
              class="form-input"
              @focus="(e) => { const target = e.target as HTMLInputElement; if (target && shouldUseVirtualKeyboard('text')) openVirtualKeyboard(target, 'text') }"
              required
            />
          </div>

          <div class="form-group">
            <label>Email: <span class="required">*</span></label>
            <input 
              v-model="invoiceData.email" 
              type="email" 
              :inputmode="shouldUseVirtualKeyboard('email') ? 'none' : 'email'"
              :readonly="shouldUseVirtualKeyboard('email')"
              placeholder="correo@ejemplo.com"
              class="form-input"
              @focus="(e) => { const target = e.target as HTMLInputElement; if (target && shouldUseVirtualKeyboard('email')) openVirtualKeyboard(target, 'email') }"
              required
            />
          </div>

          <div class="form-group">
            <label>Teléfono: <span class="required">*</span></label>
            <p class="form-help-text">Debe empezar por 3 y tener 10 dígitos</p>
            <input 
              v-model="invoiceData.phone" 
              type="tel" 
              inputmode="numeric"
              pattern="[0-9]*"
              placeholder="Ej: 3001234567"
              class="form-input"
              @focus="(e) => { const target = e.target as HTMLInputElement; if (target && shouldUseVirtualKeyboard('numeric')) openVirtualKeyboard(target, 'numeric') }"
              maxlength="10"
              required
            />
          </div>

          <div class="button-group">
            <button 
              class="continue-btn" 
              @click="proceedToPayment"
              :disabled="!isInvoiceFormValid"
            >
              Continuar al Pago
            </button>
            <button class="back-btn" @click="goBackToDocumentModal">
              ← Atrás
            </button>
          </div>
        </div>
      </div>
    </div>

    <!-- Modal: Teléfono para consumidor final -->
    <div v-if="showTelefonoConsumidorModal" class="modal-overlay">
      <div class="modal-content invoice-modal">
        <h2 class="modal-title">Teléfono de Contacto</h2>
        <div class="invoice-form">
          <div class="form-group">
            <label>Ingresa tu número de teléfono: <span class="required">*</span></label>
            <p class="form-help-text">Necesitamos tu teléfono para avisarte cuando tu pedido esté listo</p>
            <!-- Label grande centrado mostrando números digitados -->
            <div 
              class="telefono-display"
              :class="{ 'has-value': telefonoConsumidor && telefonoConsumidor.trim() !== '' }"
              @click="() => { if (typeof document !== 'undefined') { const input = document.querySelector('.telefono-input-hidden') as HTMLInputElement; if (input) input.focus() } }"
            >
              {{ telefonoConsumidor || '---' }}
            </div>
            <!-- Input oculto para capturar teclado -->
            <input 
              v-model="telefonoConsumidor" 
              type="tel" 
              :inputmode="shouldUseVirtualKeyboard('numeric') ? 'none' : 'numeric'"
              :pattern="shouldUseVirtualKeyboard('numeric') ? undefined : '[0-9]*'"
              :readonly="shouldUseVirtualKeyboard('numeric')"
              placeholder=""
              class="form-input telefono-input-hidden"
              ref="telefonoInputConsumidor"
              @focus="(e) => { const target = e.target as HTMLInputElement; if (target && shouldUseVirtualKeyboard('numeric')) { setTimeout(() => openVirtualKeyboard(target, 'numeric'), 100) } }"
              @keyup.enter="confirmTelefonoConsumidor"
              @keyup.delete="telefonoConsumidor = ''"
              @keyup.backspace="telefonoConsumidor = ''"
              required
              autofocus
            />
          </div>
          <div class="button-group">
            <button 
              class="continue-btn" 
              @click="confirmTelefonoConsumidor"
              :disabled="!telefonoConsumidor || telefonoConsumidor.length !== 10 || !telefonoConsumidor.startsWith('3')"
            >
              Continuar
            </button>
            <button class="back-btn" @click="cancelTelefonoConsumidor">
              ← Atrás
            </button>
          </div>
        </div>
      </div>
    </div>

    <!-- Modal: Teléfono para a nombre propio (si no tiene) -->
    <div v-if="showTelefonoPropioModal" class="modal-overlay">
      <div class="modal-content invoice-modal">
        <h2 class="modal-title">Teléfono de Contacto</h2>
        <div class="invoice-form">
          <div class="form-group">
            <label>Ingresa tu número de teléfono: <span class="required">*</span></label>
            <p class="form-help-text">Necesitamos tu teléfono para avisarte cuando tu pedido esté listo</p>
            <!-- Label grande centrado mostrando números digitados -->
            <div 
              class="telefono-display"
              :class="{ 'has-value': telefonoPropio && telefonoPropio.trim() !== '' }"
              @click="() => { if (typeof document !== 'undefined') { const input = document.querySelectorAll('.telefono-input-hidden')[1] as HTMLInputElement; if (input) input.focus() } }"
            >
              {{ telefonoPropio || '---' }}
            </div>
            <!-- Input oculto para capturar teclado -->
            <input 
              v-model="telefonoPropio" 
              type="tel" 
              :inputmode="shouldUseVirtualKeyboard('numeric') ? 'none' : 'numeric'"
              :pattern="shouldUseVirtualKeyboard('numeric') ? undefined : '[0-9]*'"
              :readonly="shouldUseVirtualKeyboard('numeric')"
              placeholder=""
              class="form-input telefono-input-hidden"
              ref="telefonoInputPropio"
              @focus="(e) => { const target = e.target as HTMLInputElement; if (target && shouldUseVirtualKeyboard('numeric')) { setTimeout(() => openVirtualKeyboard(target, 'numeric'), 100) } }"
              @keyup.enter="confirmTelefonoPropio"
              @keyup.delete="telefonoPropio = ''"
              @keyup.backspace="telefonoPropio = ''"
              required
              autofocus
            />
          </div>
          <div class="button-group">
            <button 
              class="continue-btn" 
              @click="confirmTelefonoPropio"
              :disabled="!telefonoPropio || telefonoPropio.length !== 10 || !telefonoPropio.startsWith('3')"
            >
              Continuar
            </button>
            <button class="back-btn" @click="cancelTelefonoPropio">
              ← Atrás
            </button>
          </div>
        </div>
      </div>
    </div>

    <!-- Modal: Seleccionar forma de pago -->
    <div v-if="showFormaPagoModal" class="modal-overlay">
      <div class="modal-content invoice-modal">
        <h2 class="modal-title">Selecciona la Forma de Pago</h2>
        <div class="invoice-form">
          <div v-if="loadingFormasPago" class="validating-message">
            <div class="spinner-small"></div>
            <p>Cargando formas de pago...</p>
          </div>
          <div v-else-if="formasPago.length === 0" class="form-group">
            <p class="error-message">No hay formas de pago disponibles</p>
          </div>
          <div v-else class="form-group">
            <div class="payment-options">
              <button
                v-for="fp in formasPago"
                :key="fp.codigo"
                class="payment-option-btn"
                :class="{ active: formaPagoSeleccionada === fp.codigo }"
                @click="formaPagoSeleccionada = fp.codigo"
              >
                <span class="payment-icon">{{ getPaymentIcon(fp.codigo) }}</span>
                <span class="payment-label">{{ fp.descripcion }}</span>
              </button>
            </div>
          </div>
          <div class="button-group">
            <button 
              class="continue-btn" 
              @click="confirmFormaPago"
              :disabled="!formaPagoSeleccionada || loadingFormasPago"
            >
              Continuar al Pago
            </button>
            <button class="back-btn" @click="cancelFormaPago">
              ← Atrás
            </button>
          </div>
        </div>
      </div>
    </div>

    <!-- Modal 3: Continúa en el datafono -->
    <div v-if="showPaymentModal" class="modal-overlay">
      <div class="modal-content payment-modal">
        <div class="payment-icon">💳</div>
        <h2 class="modal-title">Continúa en el Datafono</h2>
        <p class="payment-message">
          Por favor, completa el pago en el datafono físico.
        </p>
        <div class="payment-amount">
          <span class="amount-label">Total a pagar:</span>
          <span class="amount-value">${{ formatPrice(cartTotal) }}</span>
        </div>
        <div class="payment-loading">
          <div class="spinner"></div>
          <p>Esperando confirmación del pago...</p>
        </div>
        <button class="cancel-payment-btn" @click="cancelPayment">
          Cancelar Pago
        </button>
      </div>
    </div>

    <!-- Teclado Virtual Personalizado -->
    <div v-if="showVirtualKeyboard" class="virtual-keyboard-overlay" @click.self="closeVirtualKeyboard">
      <div class="virtual-keyboard" @click.stop>
        <div class="virtual-keyboard-header">
          <span>Teclado Virtual</span>
          <button @click="closeVirtualKeyboard" class="close-keyboard-btn">✕</button>
        </div>
        <div class="virtual-keyboard-body">
          <!-- Teclado Numérico -->
          <div v-if="activeInput.type === 'numeric'" class="keyboard-numeric">
            <div class="keyboard-row">
              <button @click="virtualKeyPress('1')" class="keyboard-key">1</button>
              <button @click="virtualKeyPress('2')" class="keyboard-key">2</button>
              <button @click="virtualKeyPress('3')" class="keyboard-key">3</button>
            </div>
            <div class="keyboard-row">
              <button @click="virtualKeyPress('4')" class="keyboard-key">4</button>
              <button @click="virtualKeyPress('5')" class="keyboard-key">5</button>
              <button @click="virtualKeyPress('6')" class="keyboard-key">6</button>
            </div>
            <div class="keyboard-row">
              <button @click="virtualKeyPress('7')" class="keyboard-key">7</button>
              <button @click="virtualKeyPress('8')" class="keyboard-key">8</button>
              <button @click="virtualKeyPress('9')" class="keyboard-key">9</button>
            </div>
            <div class="keyboard-row">
              <button @click="virtualKeyPress('-')" class="keyboard-key">-</button>
              <button @click="virtualKeyPress('0')" class="keyboard-key">0</button>
              <button @click="virtualKeyPress('backspace')" class="keyboard-key keyboard-key-backspace">⌫</button>
            </div>
          </div>
          
          <!-- Teclado Texto/Email -->
          <div v-else class="keyboard-text">
            <div class="keyboard-row">
              <button @click="virtualKeyPress(isShiftActive ? 'Q' : 'q')" class="keyboard-key">{{ isShiftActive ? 'Q' : 'q' }}</button>
              <button @click="virtualKeyPress(isShiftActive ? 'W' : 'w')" class="keyboard-key">{{ isShiftActive ? 'W' : 'w' }}</button>
              <button @click="virtualKeyPress(isShiftActive ? 'E' : 'e')" class="keyboard-key">{{ isShiftActive ? 'E' : 'e' }}</button>
              <button @click="virtualKeyPress(isShiftActive ? 'R' : 'r')" class="keyboard-key">{{ isShiftActive ? 'R' : 'r' }}</button>
              <button @click="virtualKeyPress(isShiftActive ? 'T' : 't')" class="keyboard-key">{{ isShiftActive ? 'T' : 't' }}</button>
              <button @click="virtualKeyPress(isShiftActive ? 'Y' : 'y')" class="keyboard-key">{{ isShiftActive ? 'Y' : 'y' }}</button>
              <button @click="virtualKeyPress(isShiftActive ? 'U' : 'u')" class="keyboard-key">{{ isShiftActive ? 'U' : 'u' }}</button>
              <button @click="virtualKeyPress(isShiftActive ? 'I' : 'i')" class="keyboard-key">{{ isShiftActive ? 'I' : 'i' }}</button>
              <button @click="virtualKeyPress(isShiftActive ? 'O' : 'o')" class="keyboard-key">{{ isShiftActive ? 'O' : 'o' }}</button>
              <button @click="virtualKeyPress(isShiftActive ? 'P' : 'p')" class="keyboard-key">{{ isShiftActive ? 'P' : 'p' }}</button>
            </div>
            <div class="keyboard-row">
              <button @click="virtualKeyPress(isShiftActive ? 'A' : 'a')" class="keyboard-key">{{ isShiftActive ? 'A' : 'a' }}</button>
              <button @click="virtualKeyPress(isShiftActive ? 'S' : 's')" class="keyboard-key">{{ isShiftActive ? 'S' : 's' }}</button>
              <button @click="virtualKeyPress(isShiftActive ? 'D' : 'd')" class="keyboard-key">{{ isShiftActive ? 'D' : 'd' }}</button>
              <button @click="virtualKeyPress(isShiftActive ? 'F' : 'f')" class="keyboard-key">{{ isShiftActive ? 'F' : 'f' }}</button>
              <button @click="virtualKeyPress(isShiftActive ? 'G' : 'g')" class="keyboard-key">{{ isShiftActive ? 'G' : 'g' }}</button>
              <button @click="virtualKeyPress(isShiftActive ? 'H' : 'h')" class="keyboard-key">{{ isShiftActive ? 'H' : 'h' }}</button>
              <button @click="virtualKeyPress(isShiftActive ? 'J' : 'j')" class="keyboard-key">{{ isShiftActive ? 'J' : 'j' }}</button>
              <button @click="virtualKeyPress(isShiftActive ? 'K' : 'k')" class="keyboard-key">{{ isShiftActive ? 'K' : 'k' }}</button>
              <button @click="virtualKeyPress(isShiftActive ? 'L' : 'l')" class="keyboard-key">{{ isShiftActive ? 'L' : 'l' }}</button>
            </div>
            <div class="keyboard-row">
              <button @click="toggleShift" class="keyboard-key keyboard-key-shift" :class="{ 'active': isShiftActive }">⇧</button>
              <button @click="virtualKeyPress(isShiftActive ? 'Z' : 'z')" class="keyboard-key">{{ isShiftActive ? 'Z' : 'z' }}</button>
              <button @click="virtualKeyPress(isShiftActive ? 'X' : 'x')" class="keyboard-key">{{ isShiftActive ? 'X' : 'x' }}</button>
              <button @click="virtualKeyPress(isShiftActive ? 'C' : 'c')" class="keyboard-key">{{ isShiftActive ? 'C' : 'c' }}</button>
              <button @click="virtualKeyPress(isShiftActive ? 'V' : 'v')" class="keyboard-key">{{ isShiftActive ? 'V' : 'v' }}</button>
              <button @click="virtualKeyPress(isShiftActive ? 'B' : 'b')" class="keyboard-key">{{ isShiftActive ? 'B' : 'b' }}</button>
              <button @click="virtualKeyPress(isShiftActive ? 'N' : 'n')" class="keyboard-key">{{ isShiftActive ? 'N' : 'n' }}</button>
              <button @click="virtualKeyPress(isShiftActive ? 'M' : 'm')" class="keyboard-key">{{ isShiftActive ? 'M' : 'm' }}</button>
              <button @click="virtualKeyPress('backspace')" class="keyboard-key keyboard-key-backspace">⌫</button>
            </div>
            <div class="keyboard-row">
              <button v-if="activeInput.type === 'email'" @click="virtualKeyPress('@')" class="keyboard-key">@</button>
              <button @click="virtualKeyPress('.')" class="keyboard-key">.</button>
              <button @click="virtualKeyPress('space')" class="keyboard-key keyboard-key-space">Espacio</button>
              <button @click="virtualKeyPress('-')" class="keyboard-key">-</button>
              <button @click="virtualKeyPress('_')" class="keyboard-key">_</button>
            </div>
            <div class="keyboard-row">
              <button @click="virtualKeyPress('0')" class="keyboard-key">0</button>
              <button @click="virtualKeyPress('1')" class="keyboard-key">1</button>
              <button @click="virtualKeyPress('2')" class="keyboard-key">2</button>
              <button @click="virtualKeyPress('3')" class="keyboard-key">3</button>
              <button @click="virtualKeyPress('4')" class="keyboard-key">4</button>
              <button @click="virtualKeyPress('5')" class="keyboard-key">5</button>
              <button @click="virtualKeyPress('6')" class="keyboard-key">6</button>
              <button @click="virtualKeyPress('7')" class="keyboard-key">7</button>
              <button @click="virtualKeyPress('8')" class="keyboard-key">8</button>
              <button @click="virtualKeyPress('9')" class="keyboard-key">9</button>
            </div>
          </div>
        </div>
      </div>
    </div>

    <!-- Selector de modo de teclado - Solo visible para ADMIN -->
    <div v-if="isAdmin" class="keyboard-mode-selector">
      <label>
        <span>🔧 Modo Teclado:</span>
        <select v-model="keyboardMode" @change="onKeyboardModeChange">
          <option value="auto">Automático (inputmode)</option>
          <option value="virtual">Teclado Virtual Personalizado</option>
          <option value="hybrid">Híbrido (auto en móvil, virtual en desktop)</option>
        </select>
      </label>
    </div>

    <!-- Modal: Editar Branding (Logo y Colores) - Solo ADMIN -->
    <div v-if="showBrandingModal" class="modal-overlay" @click="showBrandingModal = false">
      <div class="modal-content" @click.stop>
        <h2 class="modal-title">Editar Logo y Colores</h2>
        <div class="invoice-form">
          <div class="form-group">
            <label>Logo de la Empresa:</label>
            <input 
              type="file" 
              accept="image/*" 
              @change="(e) => { const files = (e.target as HTMLInputElement).files; if (files && files[0]) brandingData.logo = files[0] }"
              class="form-input"
            />
          </div>
          <div class="form-group">
            <label>Seleccionar Tema Predefinido:</label>
            <select 
              v-model="selectedTheme" 
              @change="applyTheme"
              class="form-input"
            >
              <option value="">Personalizado</option>
              <option value="mcdonalds">🍔 McDonald's (Rojo/Amarillo)</option>
              <option value="burgerking">🍔 Burger King (Naranja/Amarillo)</option>
              <option value="frisby">🍗 Frisby (Azul/Amarillo)</option>
              <option value="natural">🌿 Natural (Verde/Amarillo)</option>
              <option value="profesional">💼 Profesional (Azul/Gris)</option>
            </select>
          </div>
          <div class="form-group">
            <label>Color Primario: <span class="color-preview" :style="{ backgroundColor: brandingData.color_primario }"></span></label>
            <input 
              type="color" 
              :value="brandingData.color_primario"
              @input="(e) => { brandingData.color_primario = (e.target as HTMLInputElement).value; selectedTheme = '' }"
              class="form-input color-input"
            />
          </div>
          <div class="form-group">
            <label>Color Secundario: <span class="color-preview" :style="{ backgroundColor: brandingData.color_secundario }"></span></label>
            <input 
              type="color" 
              :value="brandingData.color_secundario"
              @input="(e) => { brandingData.color_secundario = (e.target as HTMLInputElement).value; selectedTheme = '' }"
              class="form-input color-input"
            />
          </div>
          <div class="form-group">
            <label>Color de Fondo: <span class="color-preview" :style="{ backgroundColor: brandingData.color_fondo }"></span></label>
            <input 
              type="color" 
              :value="brandingData.color_fondo"
              @input="(e) => { brandingData.color_fondo = (e.target as HTMLInputElement).value; selectedTheme = '' }"
              class="form-input color-input"
            />
          </div>
          
          <div class="form-group">
            <label>Modo de Visualización:</label>
            <select v-model="currentBranding.modo_visualizacion" class="form-input">
              <option value="vertical">Vertical (Comida) - Grid con scroll vertical</option>
              <option value="horizontal">Horizontal (Otros) - Dos filas con scroll lateral</option>
            </select>
            <p class="form-help-text" style="margin-top: 0.5rem; font-size: 0.85rem; color: #666;">
              <strong>Vertical:</strong> Para comida. Muestra modal inicial, permite notas y separadores.<br>
              <strong>Horizontal:</strong> Para otros productos. Sin modal inicial, sin notas, sin separadores. Dos filas con scroll lateral.
            </p>
          </div>
          
          <!-- Sección de Videos para Protector de Pantalla -->
          <div class="form-section-divider">
            <h3>🎬 Videos Protector de Pantalla</h3>
          </div>
          
          <div class="form-group">
            <label>Video por Defecto:</label>
            <input 
              type="file" 
              accept="video/*" 
              @change="(e) => { const files = (e.target as HTMLInputElement).files; if (files && files[0]) brandingData.video_por_defecto = files[0] }"
              class="form-input"
            />
            <small>Se mostrará primero cuando haya inactividad</small>
          </div>
          
          <div class="form-group">
            <label>Video Lunes:</label>
            <input 
              type="file" 
              accept="video/*" 
              @change="(e) => { const files = (e.target as HTMLInputElement).files; if (files && files[0]) brandingData.video_lunes = files[0] }"
              class="form-input"
            />
          </div>
          
          <div class="form-group">
            <label>Video Martes:</label>
            <input 
              type="file" 
              accept="video/*" 
              @change="(e) => { const files = (e.target as HTMLInputElement).files; if (files && files[0]) brandingData.video_martes = files[0] }"
              class="form-input"
            />
          </div>
          
          <div class="form-group">
            <label>Video Miércoles:</label>
            <input 
              type="file" 
              accept="video/*" 
              @change="(e) => { const files = (e.target as HTMLInputElement).files; if (files && files[0]) brandingData.video_miercoles = files[0] }"
              class="form-input"
            />
          </div>
          
          <div class="form-group">
            <label>Video Jueves:</label>
            <input 
              type="file" 
              accept="video/*" 
              @change="(e) => { const files = (e.target as HTMLInputElement).files; if (files && files[0]) brandingData.video_jueves = files[0] }"
              class="form-input"
            />
          </div>
          
          <div class="form-group">
            <label>Video Viernes:</label>
            <input 
              type="file" 
              accept="video/*" 
              @change="(e) => { const files = (e.target as HTMLInputElement).files; if (files && files[0]) brandingData.video_viernes = files[0] }"
              class="form-input"
            />
          </div>
          
          <div class="form-group">
            <label>Video Sábado:</label>
            <input 
              type="file" 
              accept="video/*" 
              @change="(e) => { const files = (e.target as HTMLInputElement).files; if (files && files[0]) brandingData.video_sabado = files[0] }"
              class="form-input"
            />
          </div>
          
          <div class="form-group">
            <label>Video Domingo:</label>
            <input 
              type="file" 
              accept="video/*" 
              @change="(e) => { const files = (e.target as HTMLInputElement).files; if (files && files[0]) brandingData.video_domingo = files[0] }"
              class="form-input"
            />
          </div>
          
          <button 
            class="continue-btn" 
            @click="saveBranding"
            :disabled="uploadingImage"
          >
            {{ uploadingImage ? 'Guardando...' : 'Guardar' }}
          </button>
          <button 
            class="continue-btn" 
            style="background: #666; margin-top: 0.5rem;"
            @click="showBrandingModal = false"
          >
            Cancelar
          </button>
        </div>
      </div>
    </div>

    <!-- Modal: Editar Imagen de Grupo - Solo ADMIN -->
    <div v-if="showGrupoImageModal" class="modal-overlay" @click="() => { showGrupoImageModal = false; notaEnEdicion.value = null; }">
      <div class="modal-content" @click.stop style="max-width: 800px; max-height: 90vh; overflow-y: auto;">
        <h2 class="modal-title">Editar Categoría: {{ editingGrupoDescrip || editingGrupo }}</h2>
        <div class="invoice-form">
          <!-- Sección: Imagen -->
          <div class="form-group">
            <label>Imagen:</label>
            <input 
              type="file" 
              accept="image/*" 
              @change="(e) => { const files = (e.target as HTMLInputElement).files; if (files && files[0]) saveGrupoImage(files[0]) }"
              class="form-input"
            />
          </div>
          
          <!-- Sección: Notas Rápidas -->
          <div class="form-group" style="margin-top: 2rem; border-top: 2px solid #ddd; padding-top: 1.5rem;">
            <label style="font-size: 1.2rem; font-weight: bold; margin-bottom: 1rem; display: block;">
              Opciones Rápidas para esta Categoría
            </label>
            <p style="color: #666; margin-bottom: 1rem; font-size: 0.9rem;">
              Estas opciones aparecerán como botones cuando los usuarios agreguen notas a productos de esta categoría.
            </p>
            
            <!-- Lista de notas rápidas existentes -->
            <div v-if="notasRapidasCategoria.length > 0" style="margin-bottom: 1.5rem;">
              <div 
                v-for="nota in notasRapidasCategoria" 
                :key="nota.id"
                style="position: relative; margin-bottom: 0.5rem;"
              >
                <button 
                  @click="notaEnEdicion = notaEnEdicion === nota.id ? null : nota.id"
                  class="continue-btn"
                  style="width: 100%; padding: 0.6rem 1rem; font-size: 0.9rem; text-align: left; background: #f5f5f5; color: #333; border: 1px solid #ddd;"
                >
                  {{ nota.texto }}
                </button>
                <!-- Botones de editar/eliminar que aparecen cuando se hace click -->
                <div 
                  v-if="notaEnEdicion === nota.id"
                  style="position: absolute; top: 100%; left: 0; right: 0; margin-top: 0.25rem; display: flex; gap: 0.5rem; z-index: 10;"
                >
                  <button 
                    @click.stop="editarNotaRapida(nota)"
                    class="continue-btn"
                    style="flex: 1; padding: 0.5rem; font-size: 0.85rem; background: #4CAF50;"
                  >
                    ✏️ Editar
                  </button>
                  <button 
                    @click.stop="eliminarNotaRapida(nota.id)"
                    class="continue-btn"
                    style="flex: 1; padding: 0.5rem; font-size: 0.85rem; background: #f44336;"
                  >
                    🗑️ Eliminar
                  </button>
                </div>
              </div>
            </div>
            <div v-else style="padding: 1rem; background: #f9f9f9; border-radius: 8px; color: #666; margin-bottom: 1rem;">
              No hay opciones rápidas para esta categoría. Agrega una nueva abajo.
            </div>
            
            <!-- Formulario para agregar/editar nota rápida -->
            <div style="background: #f9f9f9; padding: 1.5rem; border-radius: 8px; border: 2px dashed #ddd;">
              <h3 style="margin-top: 0; margin-bottom: 1rem; font-size: 1rem;">
                {{ editandoNotaRapida ? 'Editar' : 'Agregar Nueva' }} Opción Rápida
              </h3>
              <div class="form-group">
                <label style="display: block; margin-bottom: 0.5rem; font-weight: 500;">Texto:</label>
                <input 
                  v-model="nuevaNotaRapidaTexto"
                  type="text"
                  placeholder="Ej: SIN CEBOLLA, SIN SALSA TARTARA, etc."
                  class="form-input nota-rapida-input"
                  :inputmode="shouldUseVirtualKeyboard('text') ? 'none' : 'text'"
                  :readonly="shouldUseVirtualKeyboard('text')"
                  @keyup.enter="guardarNotaRapida"
                  @click="handleNotaRapidaInputClick"
                  @focus="(e) => { const target = e.target as HTMLInputElement; if (target && shouldUseVirtualKeyboard('text')) { if (typeof window !== 'undefined' && window.setTimeout) { window.setTimeout(() => openVirtualKeyboard(target, 'text'), 100) } } }"
                  style="width: 100%; box-sizing: border-box;"
                  ref="notaRapidaInput"
                />
              </div>
              <div style="display: flex; gap: 0.5rem; margin-top: 1rem;">
                <button 
                  @click="guardarNotaRapida"
                  class="continue-btn"
                  :disabled="!nuevaNotaRapidaTexto || nuevaNotaRapidaTexto.trim() === ''"
                  style="flex: 1; padding: 0.75rem 1.2rem;"
                >
                  {{ editandoNotaRapida ? '💾 Guardar' : '➕ Agregar' }}
                </button>
                <button 
                  v-if="editandoNotaRapida"
                  @click="cancelarEdicionNotaRapida"
                  class="continue-btn"
                  style="flex: 1; padding: 0.75rem 1.2rem; background: #666;"
                >
                  Cancelar
                </button>
              </div>
            </div>
          </div>
          
          <div style="display: flex; gap: 0.5rem; margin-top: 1.5rem;">
            <button 
              class="continue-btn" 
              style="background: #666; flex: 1;"
              @click="showGrupoImageModal = false"
            >
              Cerrar
            </button>
          </div>
        </div>
      </div>
    </div>

    <!-- Modal: Editar Imagen y Características de Material - Solo ADMIN -->
    <div v-if="showMaterialImageModal" class="modal-overlay" @click="showMaterialImageModal = false">
      <div class="modal-content" @click.stop>
        <h2 class="modal-title">Editar Producto: {{ editingMaterial }}</h2>
        <div class="invoice-form">
          <div class="form-group">
            <label>Imagen:</label>
            <input 
              type="file" 
              accept="image/*" 
              @change="(e) => { const files = (e.target as HTMLInputElement).files; if (files && files[0]) saveMaterialImage(files[0]) }"
              class="form-input"
            />
            <div v-if="currentMaterialImage" class="current-image-preview">
              <p>Imagen actual:</p>
              <img :src="currentMaterialImage" alt="Imagen actual" />
            </div>
          </div>
          <div class="form-group">
            <label>Características:</label>
            <textarea 
              v-model="materialEditData.caracteristicas"
              class="form-input"
              rows="5"
              placeholder="Ingrese las características del producto..."
            ></textarea>
          </div>
          <button 
            class="continue-btn" 
            @click="saveMaterialImage()"
            :disabled="uploadingImage"
          >
            {{ uploadingImage ? 'Guardando...' : 'Guardar Cambios' }}
          </button>
          <button 
            class="continue-btn" 
            style="background: #666; margin-top: 0.5rem;"
            @click="showMaterialImageModal = false"
          >
            Cancelar
          </button>
        </div>
      </div>
    </div>

    <!-- Modal: Configurar Caja Autopago (IP Datafono) - Solo ADMIN -->
    <div v-if="showCajaConfigModal" class="modal-overlay" @click="showCajaConfigModal = false">
      <div class="modal-content" @click.stop>
        <h2 class="modal-title">Configurar Caja Autopago</h2>
        <div class="invoice-form">
          <div class="form-group">
            <label>Nombre de la Caja:</label>
            <input 
              v-model="cajaConfig.nombre" 
              type="text" 
              placeholder="Ej: Caja Principal, Caja 1"
              class="form-input"
            />
          </div>
          <div class="form-group">
            <label>IP del Datafono (Servidor Local):</label>
            <input 
              v-model="cajaConfig.ip_datafono" 
              type="text" 
              placeholder="Ej: 10.8.0.5 o 192.168.1.100"
              class="form-input"
            />
            <small>IP del servidor local donde está el datafono (vía WireGuard)</small>
          </div>
          <div class="form-group">
            <label>Puerto del Datafono:</label>
            <input 
              v-model.number="cajaConfig.puerto_datafono" 
              type="number" 
              placeholder="8080"
              class="form-input"
            />
          </div>
          <div class="form-group">
            <label>
              <input 
                type="checkbox" 
                v-model="cajaConfig.modo_mock"
              />
              Modo Mock (Simular respuestas sin datafono físico)
            </label>
          </div>
          <div v-if="cajaConfig.modo_mock" class="form-group">
            <label>Probabilidad de Éxito (0.0 a 1.0):</label>
            <input 
              v-model.number="cajaConfig.probabilidad_exito" 
              type="number" 
              min="0" 
              max="1" 
              step="0.1"
              placeholder="0.8"
              class="form-input"
            />
            <small>0.8 = 80% de éxito, 0.5 = 50% de éxito, etc.</small>
          </div>
          <div class="form-group">
            <label>
              <input 
                type="checkbox" 
                v-model="cajaConfig.modo_mock_dian"
              />
              Modo Mock DIAN
            </label>
            <small>Si está activado, simula el envío a DIAN sin procesar realmente (espera 4 segundos y retorna exitoso)</small>
          </div>
          <div class="form-group">
            <label>
              <input 
                type="checkbox" 
                v-model="cajaConfig.activa"
              />
              Caja Activa
            </label>
          </div>
          <button 
            class="continue-btn" 
            @click="saveCajaConfig"
            :disabled="!cajaConfig.nombre || !cajaConfig.ip_datafono"
          >
            Guardar Configuración
          </button>
          <button 
            class="continue-btn secondary" 
            @click="showCajaConfigModal = false"
          >
            Cancelar
          </button>
        </div>
      </div>
    </div>

    <!-- Modal: Vista de Producto (foto 3D + precio + características) -->
    <div
      v-if="showProductViewModal"
      class="modal-overlay product-view-overlay"
      @click="showProductViewModal = false"
    >
      <div class="modal-content product-view-modal" @click.stop>
        <button class="close-product-view" @click="showProductViewModal = false">✕</button>
        <div class="product-view-container">
          <div :class="['product-view-image-container', { 'has-image': viewingProduct?.imagen_url }]">
            <img
              v-if="viewingProduct?.imagen_url"
              :src="viewingProduct.imagen_url"
              :alt="viewingProduct?.name"
              class="product-view-image"
            />
            <span v-else class="product-view-emoji">{{ viewingProduct?.emoji }}</span>
            <!-- Precio superpuesto bajo la imagen, sin texto 'Precio' -->
            <div class="product-view-price-tag">
              ${{ formatPrice(viewingProduct?.price || 0) }}
            </div>
          </div>
          <div class="product-view-info">
            <h2 class="product-view-name">{{ viewingProduct?.name }}</h2>
            <p class="product-view-description">{{ viewingProduct?.description }}</p>

            <div v-if="productMaterialData?.caracteristicas" class="product-view-characteristics">
              <h3>Características:</h3>
              <p>{{ productMaterialData.caracteristicas }}</p>
            </div>

            <button
              class="continue-btn add-to-cart-from-view"
              @click="addToCart(viewingProduct); showProductViewModal = false"
            >
              + Agregar al Carrito
            </button>
          </div>
        </div>
      </div>
    </div>

    <!-- Header -->
    <header class="autopago-header" :class="{ 'modo-horizontal-header': esModoHorizontal }">
      <div 
        class="logo-section" 
        @click="handleLogoClick" 
        @dblclick="handleLogoDoubleClick"
        :class="{ 'editable': isAdmin }"
      >
        <div class="logo-left">
          <img 
            v-if="currentBranding?.logo_url" 
            :src="currentBranding.logo_url" 
            alt="Logo de la empresa" 
            class="company-logo"
          />
          <h1 v-else class="logo">{{ companyName }}</h1>
        </div>
        <div class="logo-right">
          <h1 v-if="currentBranding?.logo_url" class="logo">{{ companyName }}</h1>
          <!-- Búsqueda debajo del nombre de empresa (solo modo horizontal) -->
          <div v-if="esModoHorizontal" class="search-in-header">
            <input 
              v-model="searchQuery" 
              type="text" 
              :inputmode="shouldUseVirtualKeyboard('text') ? 'none' : 'text'"
              :readonly="shouldUseVirtualKeyboard('text')"
              placeholder="🔍 Buscar..." 
              class="search-input-header"
              @focus="(e) => { const target = e.target as HTMLInputElement; if (target && shouldUseVirtualKeyboard('text')) openVirtualKeyboard(target, 'text') }"
            />
          </div>
          <!-- Carrito debajo del buscador (solo modo horizontal) -->
          <div 
            v-if="cartTotalItems > 0 && esModoHorizontal" 
            class="cart-badge-header" 
            @click="showCart = true"
          >
            <div class="cart-badge">
              🛒
            </div>
            <span class="cart-label-header">
              Carrito de Compras ({{ cartTotalItems }})
            </span>
          </div>
          <div v-if="orderType && esModoComida" class="order-type-badges">
            <p 
              class="order-type-badge clickable"
              @click="showOrderTypeModal = true"
              title="Cambiar tipo de pedido"
            >
              {{ orderType === 'takeaway' ? '🥡 Para Llevar' : '🍽️ Para Comer Aquí' }}
            </p>
            <p 
              v-if="orderType === 'dinein'" 
              class="order-type-badge clickable mesa-badge"
              @click="showMesaModal = true"
              :title="mesaNumber ? 'Cambiar mesa' : 'Seleccionar mesa'"
            >
              🪑 {{ mesaNumber ? `Mesa ${mesaNumber}` : 'Sin Mesa' }}
            </p>
          </div>
        </div>
      </div>
      
      <!-- Categorías en el header (solo modo horizontal) - Tercera columna -->
      <div v-if="esModoHorizontal" class="categories-in-header-wrapper">
        <!-- Controles admin arriba de categorías (solo si es admin) -->
        <div v-if="isAdmin" class="header-controls-horizontal-admin">
          <button 
            @click="openCajaConfigModal"
            class="header-config-btn"
            title="Configurar IP del Datafono"
          >
            ⚙️ Datafono
          </button>
          <button 
            v-if="!showUserSwitchModal"
            @click="showUserSwitchModal = true"
            class="header-config-btn header-logout-btn"
            title="Volver a CAJAGC"
          >
            🚪 Salir
          </button>
        </div>
        <div class="categories-in-header">
          <button
            v-for="category in categories"
            :key="category.id"
            :class="['category-btn-header', { active: selectedCategory === category.id }]"
            @click="selectedCategory = category.id"
          >
            <img 
              v-if="category.imagen_url" 
              :src="category.imagen_url" 
              :alt="category.name"
              class="category-img-header"
            />
            <span v-else class="category-icon-header">{{ category.icon }}</span>
            <span class="category-name-header">{{ category.name }}</span>
            <button 
              v-if="isAdmin" 
              class="edit-btn-small-header" 
              @click.stop="openGrupoImageEditor(category.gm_codigo || category.id)"
              title="Editar imagen de categoría"
            >
              ✏️
            </button>
          </button>
        </div>
      </div>
      
      <!-- Búsqueda y controles integrados en el header (solo modo vertical) -->
      <div v-if="esModoComida" class="header-controls">
        <!-- Botón para configurar caja autopago (solo ADMIN) -->
        <button 
          v-if="isAdmin" 
          @click="openCajaConfigModal"
          class="header-config-btn"
          title="Configurar IP del Datafono"
        >
          ⚙️ Datafono
        </button>
        <!-- Botón de cerrar sesión (solo ADMIN) -->
        <button 
          v-if="isAdmin && !showUserSwitchModal"
          @click="showUserSwitchModal = true"
          class="header-config-btn header-logout-btn"
          title="Volver a CAJAGC"
        >
          🚪 Salir
        </button>
        <input 
          v-model="searchQuery" 
          type="text" 
          :inputmode="shouldUseVirtualKeyboard('text') ? 'none' : 'text'"
          :readonly="shouldUseVirtualKeyboard('text')"
          placeholder="🔍 Buscar..." 
          class="header-search-input"
          @focus="(e) => { const target = e.target as HTMLInputElement; if (target && shouldUseVirtualKeyboard('text')) openVirtualKeyboard(target, 'text') }"
        />
        <!-- Switch para columnas -->
        <div class="header-columns-switch">
          <button 
            :class="['header-column-btn', { active: columnsCount === 2 }]"
            @click="columnsCount = 2"
            title="2 columnas"
          >
            <span>▦</span>
          </button>
          <button 
            :class="['header-column-btn', { active: columnsCount === 3 }]"
            @click="columnsCount = 3"
            title="3 columnas"
          >
            <span>▦▦</span>
          </button>
        </div>
      </div>
      
      <!-- Carrito flotante a la derecha solo en modo comida (vertical) -->
      <div class="cart-badge" v-if="cartTotalItems > 0 && esModoComida" @click="showCart = true">
        <span class="badge-count">{{ cartTotalItems }}</span>
        🛒
      </div>
    </header>
    
    <!-- Categorías (solo modo vertical) -->
    <div v-if="esModoComida" class="categories-section">
      <button
        v-for="category in categories"
        :key="category.id"
        :class="['category-btn', { active: selectedCategory === category.id }]"
        @click="selectedCategory = category.id"
      >
        <img 
          v-if="category.imagen_url" 
          :src="category.imagen_url" 
          :alt="category.name"
          class="category-img"
        />
        <span v-else class="category-icon">{{ category.icon }}</span>
        <span class="category-name">{{ category.name }}</span>
        <button 
          v-if="isAdmin" 
          class="edit-btn-small" 
          @click.stop="openGrupoImageEditor(category.gm_codigo || category.id)"
          title="Editar imagen de categoría"
        >
          ✏️
        </button>
      </button>
    </div>

    <!-- Productos -->
    <div class="products-section" :class="{ 
      'columns-2': columnsCount === 2 && esModoComida, 
      'columns-3': columnsCount === 3 && esModoComida,
      'modo-horizontal': esModoHorizontal
    }">
      <!-- Modo horizontal: dos filas con scroll lateral -->
      <template v-if="esModoHorizontal">
        <div class="horizontal-row">
          <div 
            v-for="(product, index) in filteredProducts.filter((_, i) => i % 2 === 0)" 
            :key="product.id"
            class="product-card product-card-horizontal"
          >
            <div class="product-horizontal-content">
              <div 
                :class="['product-image product-image-horizontal', { 'has-image': product.imagen_url }]"
                @click="isAdmin ? openMaterialImageEditor(product.codigo || product.id) : openProductView(product)"
              >
                <img 
                  v-if="product.imagen_url" 
                  :src="product.imagen_url" 
                  :alt="product.name"
                  class="product-img product-img-horizontal"
                />
                <span v-else class="product-emoji">{{ product.emoji }}</span>
                <button 
                  v-if="isAdmin" 
                  class="edit-btn-overlay" 
                  @click.stop="openMaterialImageEditor(product.codigo || product.id)"
                  title="Editar imagen y características"
                >
                  ✏️
                </button>
              </div>
              <div class="product-info product-info-horizontal" @click="openProductView(product)">
                <h3 class="product-name product-name-horizontal">{{ product.name }}</h3>
                <p class="product-description product-description-horizontal">{{ product.description }}</p>
                <div class="product-footer product-footer-horizontal">
                  <span class="product-price" @click.stop="openProductView(product)">${{ formatPrice(product.price) }}</span>
                  <button class="add-btn" @click.stop="addToCart(product)">+ Agregar</button>
                </div>
              </div>
            </div>
          </div>
        </div>
        <div class="horizontal-row">
          <div 
            v-for="(product, index) in filteredProducts.filter((_, i) => i % 2 === 1)" 
            :key="product.id"
            class="product-card product-card-horizontal"
          >
            <div class="product-horizontal-content">
              <div 
                :class="['product-image product-image-horizontal', { 'has-image': product.imagen_url }]"
                @click="isAdmin ? openMaterialImageEditor(product.codigo || product.id) : openProductView(product)"
              >
                <img 
                  v-if="product.imagen_url" 
                  :src="product.imagen_url" 
                  :alt="product.name"
                  class="product-img product-img-horizontal"
                />
                <span v-else class="product-emoji">{{ product.emoji }}</span>
                <button 
                  v-if="isAdmin" 
                  class="edit-btn-overlay" 
                  @click.stop="openMaterialImageEditor(product.codigo || product.id)"
                  title="Editar imagen y características"
                >
                  ✏️
                </button>
              </div>
              <div class="product-info product-info-horizontal" @click="openProductView(product)">
                <h3 class="product-name product-name-horizontal">{{ product.name }}</h3>
                <p class="product-description product-description-horizontal">{{ product.description }}</p>
                <div class="product-footer product-footer-horizontal">
                  <span class="product-price" @click.stop="openProductView(product)">${{ formatPrice(product.price) }}</span>
                  <button class="add-btn" @click.stop="addToCart(product)">+ Agregar</button>
                </div>
              </div>
            </div>
          </div>
        </div>
      </template>
      <!-- Modo vertical (comida): grid normal -->
      <div 
        v-else
        v-for="product in filteredProducts" 
        :key="product.id"
        class="product-card"
      >
        <div 
          :class="['product-image', { 'has-image': product.imagen_url }]"
          @click="isAdmin ? openMaterialImageEditor(product.codigo || product.id) : openProductView(product)"
        >
          <img 
            v-if="product.imagen_url" 
            :src="product.imagen_url" 
            :alt="product.name"
            class="product-img"
          />
          <span v-else class="product-emoji">{{ product.emoji }}</span>
          <button 
            v-if="isAdmin" 
            class="edit-btn-overlay" 
            @click.stop="openMaterialImageEditor(product.codigo || product.id)"
            title="Editar imagen y características"
          >
            ✏️
          </button>
        </div>
        <div class="product-info" @click="openProductView(product)">
          <h3 class="product-name">{{ product.name }}</h3>
          <p class="product-description">{{ product.description }}</p>
          <div class="product-footer">
            <span class="product-price" @click.stop="openProductView(product)">${{ formatPrice(product.price) }}</span>
            <button class="add-btn" @click.stop="addToCart(product)">+ Agregar</button>
          </div>
        </div>
      </div>
    </div>

    <!-- Carrito Sidebar -->
    <div v-if="showCart" class="cart-overlay" @click="showCart = false">
      <div class="cart-sidebar" @click.stop>
        <div class="cart-header">
          <h2>Tu Pedido</h2>
          <button class="close-btn" @click="showCart = false">✕</button>
        </div>

        <!-- Total y botón de pago arriba -->
        <div v-if="cart.length > 0" class="cart-footer-top">
          <div class="cart-totals">
            <div class="total-line total-final">
              <span>Total:</span>
              <span>${{ formatPrice(cartTotal) }}</span>
            </div>
          </div>
          <div class="cart-actions-top">
            <button v-if="esModoComida" class="add-separator-btn" @click="addSeparator" title="Agregar Separador">
              ➕ Separador
            </button>
            <button class="checkout-btn" @click="proceedToCheckout">
              Continuar al Pago
            </button>
          </div>
        </div>

        <!-- Items del carrito con scroll -->
        <div class="cart-items-scrollable" v-if="cart.length > 0">
          <div 
            v-for="(item, index) in cart" 
            :key="`${item.id}-${index}`" 
            class="cart-item"
            :class="{ 
              'cart-item-separator': item.isSeparator,
              'dragging': draggedItemIndex === index,
              'drag-over': draggedItemIndex !== null && draggedItemIndex !== index
            }"
            draggable="true"
            @dragstart="handleDragStart(index, $event)"
            @dragend="handleDragEnd"
            @dragover.prevent="handleDragOver(index, $event)"
            @drop="handleDrop(index, $event)"
          >
            <div v-if="item.isSeparator" class="separator-content">
              <div class="separator-line"></div>
              <span class="separator-text">━━━ Separador ━━━</span>
              <div class="separator-line"></div>
              <button @click="removeFromCart(index)" class="remove-separator-btn" title="Eliminar Separador">✕</button>
            </div>
            <template v-else>
              <div class="cart-item-info">
                <span class="cart-item-emoji">{{ item.emoji }}</span>
                <div class="cart-item-details">
                  <h4>{{ item.name }}</h4>
                  <p v-if="esModoComida && item.nota && item.nota.trim() !== ''" class="cart-item-note">
                    📝 {{ item.nota }}
                  </p>
                  <p class="cart-item-price">${{ formatPrice(item.price) }}</p>
                </div>
              </div>
              <div class="cart-item-controls">
                <button 
                  v-if="esModoComida"
                  @click="openNoteEditor(index)" 
                  class="note-btn" 
                  :class="{ 'has-note': item.nota && item.nota.trim() !== '' }"
                  title="Agregar nota"
                >
                  {{ item.nota && item.nota.trim() !== '' ? '📝' : '✏️' }}
                </button>
                <button @click="decreaseQuantity(index)" class="qty-btn">-</button>
                <span class="qty-value">{{ item.quantity }}</span>
                <button @click="increaseQuantity(index)" class="qty-btn">+</button>
                <button @click="removeFromCart(index)" class="remove-btn">🗑️</button>
              </div>
            </template>
          </div>
        </div>

        <div v-else class="empty-cart">
          <p>Tu carrito está vacío</p>
          <span class="empty-emoji">🛒</span>
        </div>
      </div>
    </div>

    <!-- Modal para editar nota del item - Solo para modo comida -->
    <div v-if="editingNoteIndex !== null && esModoComida" class="modal-overlay" @click="closeNoteEditor">
      <div class="modal-content invoice-modal" @click.stop>
        <h2 class="modal-title">Nota para {{ cart[editingNoteIndex]?.name }}</h2>
        <div class="invoice-form">
          <!-- Opciones rápidas según categoría del producto -->
          <div v-if="notasRapidasDisponibles && notasRapidasDisponibles.length > 0" class="form-group">
            <label>Opciones Rápidas:</label>
            <div class="notas-rapidas-grid">
              <button
                v-for="notaRapida in notasRapidasDisponibles"
                :key="notaRapida.id"
                @click="toggleNotaRapida(notaRapida)"
                class="nota-rapida-btn"
                :class="{ 'nota-rapida-activa': isNotaRapidaActiva(notaRapida.texto) }"
              >
                {{ notaRapida.texto }}
              </button>
            </div>
          </div>
          
          <div class="form-group">
            <label>Escribe una nota personalizada:</label>
            <textarea
              v-model="tempNote"
              class="form-input note-textarea"
              :inputmode="shouldUseVirtualKeyboard('text') ? 'none' : 'text'"
              :readonly="shouldUseVirtualKeyboard('text')"
              placeholder="Escribe tu nota personalizada o selecciona una opción rápida arriba..."
              rows="4"
              maxlength="100"
              @focus="(e) => { const target = e.target as HTMLTextAreaElement; if (target && shouldUseVirtualKeyboard('text')) openVirtualKeyboard(target, 'text') }"
            ></textarea>
            <p class="form-help-text">{{ tempNote.length }}/100 caracteres</p>
          </div>
          <div class="button-group">
            <button class="continue-btn" @click="saveNote">
              Guardar Nota
            </button>
            <button class="back-btn" @click="closeNoteEditor">
              Cancelar
            </button>
          </div>
        </div>
      </div>
    </div>
    
    <!-- Protector de Pantalla (Screensaver) -->
    <div 
      v-if="showScreensaver" 
      class="screensaver-overlay"
      @click="hideScreensaver"
      @touchstart="hideScreensaver"
    >
      <div class="screensaver-video-container">
        <video
          v-if="currentVideoUrl"
          ref="screensaverVideo"
          :src="currentVideoUrl"
          autoplay
          loop
          muted
          playsinline
          class="screensaver-video"
          @loadeddata="onVideoLoaded"
        ></video>
        <div v-else class="screensaver-placeholder">
          <p>No hay video configurado</p>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
definePageMeta({
  layout: 'autopago'
})

const session = useSessionStore()
const api = useApiClient()

// Estado para cambio de usuario
const showUserSwitchModal = ref(false)
const switchingUser = ref(false)
const userSwitchForm = reactive({
  password: ''
})
const userSwitchError = ref<string | null>(null)

// Estado para secuencia de clics en el logo (solo CAJAGC)
// Secuencia: doble clic → clic → doble clic (más fácil)
// Instrucciones: Doble clic → esperar → Clic simple → esperar → Doble clic
const logoClickSequence = ref<number[]>([]) // 0 = doble clic, 1 = clic simple
const LOGO_SEQUENCE_PATTERN = [0, 1, 0] // doble clic, clic, doble clic
const LOGO_SEQUENCE_TIMEOUT = 2000 // 2 segundos de timeout entre acciones
let logoClickTimer: ReturnType<typeof setTimeout> | null = null
let pendingSingleClick: ReturnType<typeof setTimeout> | null = null

// Manejar clics en el logo
const handleLogoClick = () => {
  if (isAdmin.value) {
    // Si es admin, abrir modal de branding (comportamiento original)
    openBrandingModal()
    return
  }
  
  // Si es CAJAGC, esperar un poco para ver si viene un doble clic
  if (pendingSingleClick) {
    clearTimeout(pendingSingleClick)
    pendingSingleClick = null
  }
  
  // Esperar 300ms para ver si es parte de un doble clic
  pendingSingleClick = setTimeout(() => {
    // Es un clic simple
    logoClickSequence.value.push(1) // 1 = clic simple
    console.log('[retail] Clic simple detectado, secuencia:', logoClickSequence.value)
    
    // Limpiar timer anterior
    if (logoClickTimer) {
      clearTimeout(logoClickTimer)
    }
    
    // Verificar secuencia después de un timeout
    logoClickTimer = setTimeout(() => {
      checkLogoSequence()
    }, LOGO_SEQUENCE_TIMEOUT)
    
    pendingSingleClick = null
  }, 300)
}

// Manejar doble clic en el logo
const handleLogoDoubleClick = () => {
  if (isAdmin.value) {
    // Si es admin, no hacer nada especial con doble clic
    return
  }
  
  // Cancelar el clic simple pendiente
  if (pendingSingleClick) {
    clearTimeout(pendingSingleClick)
    pendingSingleClick = null
  }
  
  // Registrar doble clic
  logoClickSequence.value.push(0) // 0 = doble clic
  console.log('[retail] Doble clic detectado, secuencia:', logoClickSequence.value)
  
  // Limpiar timer anterior
  if (logoClickTimer) {
    clearTimeout(logoClickTimer)
  }
  
  // Verificar secuencia después de un timeout
  logoClickTimer = setTimeout(() => {
    checkLogoSequence()
  }, LOGO_SEQUENCE_TIMEOUT)
}

// Verificar si la secuencia coincide con el patrón
const checkLogoSequence = () => {
  if (logoClickSequence.value.length < LOGO_SEQUENCE_PATTERN.length) {
    // Secuencia incompleta, limpiar si es muy antigua
    if (logoClickSequence.value.length > 0) {
      console.log('[retail] Secuencia incompleta, reseteando')
      logoClickSequence.value = []
    }
    return
  }
  
  // Verificar los últimos N elementos
  const recentSequence = logoClickSequence.value.slice(-LOGO_SEQUENCE_PATTERN.length)
  
  // Comparar con el patrón: [0, 1, 0] = doble clic, clic, doble clic
  const matches = recentSequence.every((click, index) => {
    return click === LOGO_SEQUENCE_PATTERN[index]
  })
  
  if (matches) {
    console.log('[retail] ✅ Secuencia de logo detectada, abriendo modal de login')
    showUserSwitchModal.value = true
    logoClickSequence.value = [] // Limpiar secuencia
  } else {
    // No coincide, limpiar secuencia si es muy larga
    if (logoClickSequence.value.length > LOGO_SEQUENCE_PATTERN.length * 2) {
      console.log('[retail] Secuencia no coincide, reseteando')
      logoClickSequence.value = []
    }
  }
  
  // Limpiar timer
  if (logoClickTimer) {
    clearTimeout(logoClickTimer)
    logoClickTimer = null
  }
}

// Detectar si es ADMIN
const isAdmin = computed(() => {
  const isAdminValue = session.isTNSAdmin.value
  console.log('[retail] isAdmin check:', {
    isAdmin: isAdminValue,
    tnsUsername: session.tnsUsername.value,
    validation: session.validation.value,
    ousername: session.validation.value?.VALIDATE?.OUSERNAME || session.validation.value?.validation?.OUSERNAME
  })
  return isAdminValue
})

// Nombre de la empresa: usar nombre_cliente del API Key o nombre de la empresa seleccionada
const companyName = computed(() => {
  if (session.nombreCliente.value) {
    return session.nombreCliente.value
  }
  if (session.selectedEmpresa.value?.nombre) {
    return session.selectedEmpresa.value.nombre
  }
  return 'Empresa' // Fallback
})

// Categorías ahora son computed (definido más abajo después de filteredProducts)

// Composable para consultar TNS
const { fetchRecords } = useTNSRecords()
const { getConfig } = useModuleConfig()

// Estado de productos reales
const products = ref<Array<{
  id: string
  name: string
  description: string
  price: number
  emoji: string
  category: string
  stock?: number
  codigo: string
  codbarra?: string
  peso?: number
  unidad?: string
}>>([])
const loadingProducts = ref(false)
const productsError = ref<string | null>(null)

// Función para cargar validación TNS desde sessionStorage
const loadTNSValidationFromStorage = () => {
  if (!process.client) return
  
  const empresaId = session.selectedEmpresa.value?.empresaServidorId
  if (!empresaId) {
    console.log('[retail] No hay empresa seleccionada, no se puede cargar validación')
    return
  }
  
  console.log('[retail] Buscando validación TNS para empresa:', empresaId)
  
  // Buscar validación guardada en sessionStorage
  // Puede tener formato: tns_validation_{empresaId}_{userId} o tns_validation_{empresaId}_undefined
  const prefix = `tns_validation_${empresaId}_`
  let found = false
  
  for (let i = 0; i < sessionStorage.length; i++) {
    const key = sessionStorage.key(i)
    if (key && key.startsWith(prefix)) {
      const stored = sessionStorage.getItem(key)
      if (stored) {
        try {
          const data = JSON.parse(stored)
          console.log('[retail] Validación encontrada en sessionStorage:', key, data)
          
          const oSuccess = data.validation?.OSUCCESS
          const isSuccess = oSuccess === "1" || oSuccess === 1 || 
                            String(oSuccess).toLowerCase() === "true" ||
                            String(oSuccess).toLowerCase() === "si" ||
                            String(oSuccess).toLowerCase() === "yes"
          
          if (isSuccess) {
            // Verificar que no sea muy antigua (menos de 24 horas)
            const timestamp = new Date(data.timestamp)
            const now = new Date()
            const hoursDiff = (now.getTime() - timestamp.getTime()) / (1000 * 60 * 60)
            
            if (hoursDiff < 24) {
              session.setTNSValidation(data)
              console.log('[retail] ✓ Validación TNS cargada desde sessionStorage, username:', data.username)
              found = true
            } else {
              console.log('[retail] Validación TNS muy antigua, no se carga')
            }
          } else {
            console.log('[retail] Validación TNS falló anteriormente, no se carga')
          }
        } catch (e) {
          console.error('[retail] Error parseando validación:', e)
        }
      }
      if (found) break
    }
  }
  
  if (!found) {
    console.log('[retail] No se encontró validación TNS guardada para empresa:', empresaId)
  }
}

// Cargar validación TNS cuando cambia la empresa seleccionada o al montar
watch(() => session.selectedEmpresa.value?.empresaServidorId, (empresaId) => {
  if (empresaId && process.client) {
    loadTNSValidationFromStorage()
  }
}, { immediate: true })


// Funciones de caché para productos
const getProductsCacheKey = (empresaId: number) => `retail_products_${empresaId}`
const getProductsCacheTimestampKey = (empresaId: number) => `retail_products_timestamp_${empresaId}`

const saveProductsToCache = (empresaId: number, products: any[], categories: any[]) => {
  if (typeof window === 'undefined') return
  try {
    const cacheKey = getProductsCacheKey(empresaId)
    const timestampKey = getProductsCacheTimestampKey(empresaId)
    const today = new Date().toISOString().split('T')[0] // YYYY-MM-DD
    
    localStorage.setItem(cacheKey, JSON.stringify({ products, categories }))
    localStorage.setItem(timestampKey, today)
    console.log('[retail] Productos guardados en caché para empresa:', empresaId)
  } catch (error) {
    console.error('[retail] Error guardando productos en caché:', error)
  }
}

const loadProductsFromCache = (empresaId: number): { products: any[], categories: any[] } | null => {
  if (typeof window === 'undefined') return null
  try {
    const cacheKey = getProductsCacheKey(empresaId)
    const timestampKey = getProductsCacheTimestampKey(empresaId)
    
    const cachedData = localStorage.getItem(cacheKey)
    const cachedTimestamp = localStorage.getItem(timestampKey)
    const today = new Date().toISOString().split('T')[0] // YYYY-MM-DD
    
    // Si hay caché y es del día de hoy, usarlo
    if (cachedData && cachedTimestamp === today) {
      const parsed = JSON.parse(cachedData)
      console.log('[retail] Productos cargados desde caché (del día de hoy):', parsed.products?.length || 0)
      return parsed
    }
    
    // Si el caché es de otro día, limpiarlo
    if (cachedTimestamp && cachedTimestamp !== today) {
      localStorage.removeItem(cacheKey)
      localStorage.removeItem(timestampKey)
      console.log('[retail] Caché expirado, se limpiará')
    }
    
    return null
  } catch (error) {
    console.error('[retail] Error cargando productos desde caché:', error)
    return null
  }
}

const clearProductsCache = (empresaId: number) => {
  if (typeof window === 'undefined') return
  try {
    const cacheKey = getProductsCacheKey(empresaId)
    const timestampKey = getProductsCacheTimestampKey(empresaId)
    localStorage.removeItem(cacheKey)
    localStorage.removeItem(timestampKey)
    console.log('[retail] Caché de productos limpiado para empresa:', empresaId)
  } catch (error) {
    console.error('[retail] Error limpiando caché:', error)
  }
}

// Cargar productos desde TNS al montar
const loadProducts = async (forceRefresh: boolean = false) => {
  const empresaId = session.selectedEmpresa.value?.empresaServidorId
  if (!empresaId) {
    console.warn('[retail] No hay empresa seleccionada, usando productos mock')
    return
  }

  // Si es admin, forzar actualización
  const shouldForceRefresh = forceRefresh || isAdmin.value
  
  // Si no es admin y no se fuerza, intentar cargar desde caché
  if (!shouldForceRefresh) {
    const cached = loadProductsFromCache(empresaId)
    if (cached) {
      products.value = cached.products
      // NO establecer filteredProducts aquí - se establecerá por el watch o loadMasVendidos
      allGroups.value = cached.categories
      console.log('[retail] ✅ Productos cargados desde caché (del día de hoy), categorías:', cached.categories.length)
      // Si la categoría seleccionada es 'hot', cargar más vendidos
      if (selectedCategory.value === 'hot') {
        await loadMasVendidos()
      } else {
        // Si no es 'hot', el watch se encargará de filtrar
        filteredProducts.value = cached.products
      }
      return
    } else {
      // No hay caché disponible (primera vez del día o caché expirado)
      console.log('[retail] ⚠️ No hay caché disponible, cargando desde API...')
    }
  } else {
    console.log('[retail] 🔄 Forzando actualización de productos (admin o refresh manual)')
    if (isAdmin.value) {
      clearProductsCache(empresaId) // Limpiar caché si es admin
    }
  }

  // Usar 'materialprecio' para lista inicial (más rápida, sin stock/serial)
  // 
  // Esta configuración es optimizada para el catálogo de autopago:
  // - Solo incluye: MATERIAL + MATERIALSUC + GRUPMAT + GCMAT
  // - NO incluye: SALMATERIAL, BODEGA, SERIAL (evita duplicados y mejora performance)
  // 
  // Si necesitas filtrar por bodega o ver stock, usa 'materialpreciosaldo' en su lugar:
  // const config = getConfig('materialpreciosaldo')
  // const response = await fetchRecords(config, {
  //   filters: { 'BOD_CODIGO': { operator: '=', value: 'BOD001' } }
  // })
  const config = getConfig('materialprecio')
  if (!config) {
    console.error('[retail] Configuración de materiales no encontrada')
    productsError.value = 'Configuración no encontrada'
    return
  }

  loadingProducts.value = true
  productsError.value = null

  try {
    console.log('[retail] Cargando productos desde TNS...')
    
    // 'materialprecio' solo incluye: MATERIAL + MATERIALSUC + GRUPMAT + GCMAT
    // NO incluye: SALMATERIAL, BODEGA, SERIAL (por eso es más rápida y sin duplicados)
    // Filtrar solo productos con PRECIO1 > 0
    const response = await fetchRecords(config, {
      empresa_servidor_id: empresaId,
      page: 1,
      page_size: 200, // Limit inicial
      order_by: [{ field: 'CODIGO', direction: 'ASC' }],
      filters: {
        PRECIO1: { operator: '>', value: 0 }
      }
    })

    console.log('[retail] Productos recibidos:', response.data.length)

    // Agrupar productos por CODIGO (evitar duplicados si los hay)
    // 
    // NOTA: 'materialprecio' no incluye SALMATERIAL ni SERIAL, por lo que
    // normalmente NO debería haber duplicados (un producto = una fila).
    // Sin embargo, agrupamos por seguridad en caso de datos inconsistentes.
    // 
    // Si usaras 'materialpreciosaldo' o 'materialprecioserial', aquí SÍ habría
    // duplicados (un producto por bodega o por serial) y necesitarías sumar
    // el stock: existing.stock = (existing.stock || 0) + existenc
    const productsMap = new Map<string, any>()
    
    for (const row of response.data) {
      const codigo = row.CODIGO || row.codigo
      if (!codigo) continue

      if (productsMap.has(codigo)) {
        // Producto ya existe: actualizar si hay datos mejores
        const existing = productsMap.get(codigo)
        
        // Actualizar datos si están vacíos en el existente
        if (!existing.codbarra && row.CODBARRA) existing.codbarra = row.CODBARRA
        if (!existing.peso && row.PESO) existing.peso = row.PESO
        if (!existing.unidad && row.UNIDAD) existing.unidad = row.UNIDAD
        if (!existing.gm_codigo && row.GM_CODIGO) existing.gm_codigo = row.GM_CODIGO
        if (!existing.gm_descrip && row.GM_DESCRIP) existing.gm_descrip = row.GM_DESCRIP
        // Actualizar imágenes si existen
        if (row.imagen_url && !existing.imagen_url) existing.imagen_url = row.imagen_url
        if (row.grupo_imagen_url && !existing.grupo_imagen_url) existing.grupo_imagen_url = row.grupo_imagen_url
        // Actualizar precio si es mejor (mayor) - usar PRECIO1 por defecto
        const newPrice = parseFloat(row.PRECIO1 || row.precio1 || 0) || 0
        if (newPrice > existing.price) existing.price = newPrice
      } else {
        // Nuevo producto
        productsMap.set(codigo, {
          codigo,
          codbarra: row.CODBARRA || row.codbarra,
          name: row.DESCRIP || row.descrip || codigo,
          description: `${row.UNIDAD || ''} ${row.PESO ? `(${row.PESO} kg)` : ''}`.trim() || codigo,
          price: parseFloat(row.PRECIO1 || row.precio1 || 0) || 0, // Precio por defecto: PRECIO1
          stock: undefined, // materialprecio no incluye stock
          peso: row.PESO || row.peso,
          unidad: row.UNIDAD || row.unidad,
          gm_codigo: row.GM_CODIGO || row.gm_codigo,
          gm_descrip: row.GM_DESCRIP || row.gm_descrip,
          gc_codigo: row.GC_CODIGO || row.gc_codigo,
          gc_descrip: row.GC_DESCRIP || row.gc_descrip,
          costo: parseFloat(row.COSTO || row.costo || 0) || 0,
          precio1: parseFloat(row.PRECIO1 || row.precio1 || 0) || 0,
          precio2: parseFloat(row.PRECIO2 || row.precio2 || 0) || 0,
          precio3: parseFloat(row.PRECIO3 || row.precio3 || 0) || 0,
          precio4: parseFloat(row.PRECIO4 || row.precio4 || 0) || 0,
          precio5: parseFloat(row.PRECIO5 || row.precio5 || 0) || 0,
          imagen_url: row.imagen_url || null, // URL de imagen del material
          grupo_imagen_url: row.grupo_imagen_url || null, // URL de imagen del grupo
          caracteristicas: row.caracteristicas || null // Características del material
        })
      }
    }

    // Convertir a array y mapear a formato del componente
    const processedProducts = Array.from(productsMap.values()).map((p, index) => {
      // Determinar emoji según categoría (GRUPMAT)
      const categoryName = (p.gm_descrip || '').toLowerCase()
      let emoji = '📦' // Default
      let category = 'otros'
      
      if (categoryName.includes('bebida') || categoryName.includes('refresco') || categoryName.includes('agua')) {
        emoji = '🥤'
        category = 'drinks'
      } else if (categoryName.includes('hamburguesa') || categoryName.includes('burger') || categoryName.includes('carne')) {
        emoji = '🍔'
        category = 'burgers'
      } else if (categoryName.includes('papa') || categoryName.includes('frita') || categoryName.includes('snack')) {
        emoji = '🍟'
        category = 'fries'
      } else if (categoryName.includes('postre') || categoryName.includes('helado') || categoryName.includes('dulce')) {
        emoji = '🍰'
        category = 'desserts'
      } else if (categoryName.includes('pollo') || categoryName.includes('chicken') || categoryName.includes('nugget')) {
        emoji = '🍗'
        category = 'chicken'
      } else if (categoryName.includes('ensalada') || categoryName.includes('salad') || categoryName.includes('verdura')) {
        emoji = '🥗'
        category = 'salads'
      }

      return {
        id: p.codigo, // Usar código como ID único
        name: p.name,
        description: p.description,
        price: p.price,
        emoji,
        category,
        stock: p.stock !== undefined ? Math.max(0, Math.floor(p.stock)) : undefined, // Stock solo si existe
        codigo: p.codigo,
        codbarra: p.codbarra,
        peso: p.peso,
        unidad: p.unidad,
        gm_codigo: p.gm_codigo, // Código del grupo (necesario para categorías)
        gm_descrip: p.gm_descrip, // Descripción del grupo (necesario para categorías)
        imagen_url: p.imagen_url || null, // URL de imagen del material
        grupo_imagen_url: p.grupo_imagen_url || null // URL de imagen del grupo
      }
    })

    products.value = processedProducts
    filteredProducts.value = processedProducts // Inicializar productos filtrados
    
    // Extraer categorías únicas de los productos cargados (usando GM_CODIGO y GM_DESCRIP)
    const uniqueCategories = new Map<string, { codigo: string, descrip: string, imagen_url: string | null }>()
    processedProducts.forEach(p => {
      if (p.gm_codigo && p.gm_descrip) {
        if (!uniqueCategories.has(p.gm_codigo)) {
          uniqueCategories.set(p.gm_codigo, {
            codigo: p.gm_codigo,
            descrip: p.gm_descrip,
            imagen_url: p.grupo_imagen_url || null // URL de imagen del grupo
          })
        } else {
          // Si ya existe pero no tiene imagen, actualizar si este producto tiene
          const existing = uniqueCategories.get(p.gm_codigo)!
          if (!existing.imagen_url && p.grupo_imagen_url) {
            existing.imagen_url = p.grupo_imagen_url
          }
        }
      }
    })
    allGroups.value = Array.from(uniqueCategories.values())
    
    // Guardar en caché para uso futuro (siempre que se cargue desde API)
    // Esto permite que otros usuarios (CAJAGC) puedan usar el caché después
    saveProductsToCache(empresaId, processedProducts, allGroups.value)
    console.log('[retail] 💾 Productos guardados en caché para uso de otros usuarios')
    
    console.log('[retail] Productos procesados:', processedProducts.length)
    console.log('[retail] Categorías extraídas de productos:', allGroups.value.length, allGroups.value)
    
  } catch (error: any) {
    console.error('[retail] Error cargando productos:', error)
    productsError.value = error?.message || 'Error al cargar productos'
    // En caso de error, mantener productos mock como fallback
  } finally {
    loadingProducts.value = false
  }
}

// ========== FUNCIONES DE CARGA (definidas antes de onMounted y watch) ==========

const loadBranding = async () => {
  if (!session.selectedEmpresa.value) {
    console.log('[retail] No hay empresa seleccionada, no se puede cargar branding')
    return
  }
  try {
    const nit = session.selectedEmpresa.value.nit
    const empresaId = session.selectedEmpresa.value.empresaServidorId
    const tnsUsername = session.tnsUsername.value || ''
    
    console.log('[retail] Cargando branding para:', { empresaId, nit, tnsUsername })
    
    // Para GET, los parámetros van en query string
    const response = await api.get('/api/branding/empresa/', {
      empresa_servidor_id: empresaId,
      nit: nit,
      tns_username: tnsUsername
    })
    
    console.log('[retail] Branding recibido del servidor:', response)
    // Actualizar brandingData con los valores del servidor
    if (response.color_primario) {
      brandingData.value.color_primario = response.color_primario
    }
    if (response.color_secundario) {
      brandingData.value.color_secundario = response.color_secundario
    }
    if (response.color_fondo) {
      brandingData.value.color_fondo = response.color_fondo
    }
    
    // También actualizar currentBranding para mostrar el logo y videos
    currentBranding.value = {
      logo_url: response.logo_url,
      color_primario: response.color_primario || brandingData.value.color_primario,
      color_secundario: response.color_secundario || brandingData.value.color_secundario,
      color_fondo: response.color_fondo || brandingData.value.color_fondo,
      modo_teclado: (response.modo_teclado || 'auto') as 'auto' | 'virtual' | 'hybrid',
      modo_visualizacion: (response.modo_visualizacion || 'vertical') as 'vertical' | 'horizontal',
      video_por_defecto_url: response.video_por_defecto_url || null,
      video_del_dia_url: response.video_del_dia_url || null
    }
    
    // Aplicar modo_teclado desde el backend
    if (response.modo_teclado && ['auto', 'virtual', 'hybrid'].includes(response.modo_teclado)) {
      keyboardMode.value = response.modo_teclado as 'auto' | 'virtual' | 'hybrid'
    }
    
    // Aplicar colores dinámicamente al CSS usando CSS variables
    if (process.client) {
      const root = document.documentElement
      if (currentBranding.value.color_primario) {
        root.style.setProperty('--color-primario', currentBranding.value.color_primario)
      }
      if (currentBranding.value.color_secundario) {
        root.style.setProperty('--color-secundario', currentBranding.value.color_secundario)
      }
      if (currentBranding.value.color_fondo) {
        root.style.setProperty('--color-fondo', currentBranding.value.color_fondo)
      }
    }
    
    console.log('[retail] Branding cargado:', {
      brandingData: brandingData.value,
      currentBranding: currentBranding.value
    })
  } catch (error) {
    console.error('Error cargando branding:', error)
  }
}

// Cargar productos al montar (después de que se seleccione empresa)
onMounted(async () => {
  console.log('[retail] Página montada')
  
  // Cargar validación TNS desde sessionStorage si existe
  // El watch con immediate:true debería ejecutarse, pero por si acaso lo llamamos también aquí
  if (process.client && session.selectedEmpresa.value?.empresaServidorId) {
    // Pequeño delay para asegurar que sessionStorage esté disponible
    setTimeout(() => {
      loadTNSValidationFromStorage()
    }, 50)
  }
  
  // Esperar a que haya empresa seleccionada
  await nextTick()
  if (session.selectedEmpresa.value) {
    // Cargar branding primero (para aplicar colores y logo)
    await loadBranding()
    // Cargar formas de pago en paralelo (para ahorrar tiempo cuando vayan a pagar)
    loadFormasPago()
    // Cargar TODOS los productos y categorías primero (necesario para que funcionen las categorías)
    // Si es admin, forzar actualización; si no, usar caché si está disponible
    await loadProducts(isAdmin.value)
    // Asegurar que la categoría esté en 'hot' para mostrar más vendidos
    selectedCategory.value = 'hot'
    // Luego cargar productos más vendidos por defecto
    await loadMasVendidos()
  } else {
    // Si no hay empresa, usar productos mock
    console.warn('[retail] No hay empresa seleccionada, usando productos mock')
  }
})

// Watch para recargar cuando se seleccione empresa  
watch(() => session.selectedEmpresa.value?.empresaServidorId, async (newId) => {
  if (newId) {
    // Cargar branding primero (para aplicar colores y logo)
    await loadBranding()
    // Cargar configuración de caja autopago
    await loadCajaConfig()
    // Cargar formas de pago en paralelo (para ahorrar tiempo cuando vayan a pagar)
    loadFormasPago()
    // Cargar notas rápidas
    loadNotasRapidas()
    // Cargar TODOS los productos y categorías primero (necesario para que funcionen las categorías)
    // Si es admin, forzar actualización; si no, usar caché si está disponible
    await loadProducts(isAdmin.value)
    // Asegurar que la categoría esté en 'hot' para mostrar más vendidos
    selectedCategory.value = 'hot'
    // Luego cargar productos más vendidos por defecto
    await loadMasVendidos()
    
    // En modo horizontal, no mostrar modal inicial
    if (esModoHorizontal.value) {
      showOrderTypeModal.value = false
      orderType.value = null
    }
  }
})

// Mock Data - Productos (fallback si no hay empresa o error)
const mockProducts = [
  // Hamburguesas
  { id: 1, name: 'Big Burger', description: 'Carne, queso, lechuga, tomate', price: 15900, emoji: '🍔', category: 'burgers' },
  { id: 2, name: 'Cheese Burger', description: 'Doble carne y queso', price: 18900, emoji: '🍔', category: 'burgers' },
  { id: 3, name: 'Bacon Burger', description: 'Con tocino crujiente', price: 21900, emoji: '🍔', category: 'burgers' },
  { id: 4, name: 'Chicken Burger', description: 'Pollo empanizado', price: 14900, emoji: '🍔', category: 'burgers' },
  { id: 5, name: 'Veggie Burger', description: '100% vegetal', price: 12900, emoji: '🍔', category: 'burgers' },
  
  // Bebidas
  { id: 6, name: 'Coca Cola', description: '500ml', price: 3500, emoji: '🥤', category: 'drinks' },
  { id: 7, name: 'Sprite', description: '500ml', price: 3500, emoji: '🥤', category: 'drinks' },
  { id: 8, name: 'Fanta', description: '500ml', price: 3500, emoji: '🥤', category: 'drinks' },
  { id: 9, name: 'Agua', description: '500ml', price: 2000, emoji: '💧', category: 'drinks' },
  { id: 10, name: 'Jugo de Naranja', description: 'Natural', price: 4500, emoji: '🧃', category: 'drinks' },
  
  // Papas
  { id: 11, name: 'Papas Fritas', description: 'Porción regular', price: 5500, emoji: '🍟', category: 'fries' },
  { id: 12, name: 'Papas Grandes', description: 'Porción grande', price: 7500, emoji: '🍟', category: 'fries' },
  { id: 13, name: 'Papas con Queso', description: 'Con queso derretido', price: 8500, emoji: '🍟', category: 'fries' },
  
  // Postres
  { id: 14, name: 'Helado de Vainilla', description: '2 bolas', price: 4500, emoji: '🍦', category: 'desserts' },
  { id: 15, name: 'Brownie', description: 'Con helado', price: 6500, emoji: '🍰', category: 'desserts' },
  { id: 16, name: 'Torta de Chocolate', description: 'Porción', price: 5500, emoji: '🎂', category: 'desserts' },
  
  // Pollo
  { id: 17, name: 'Nuggets (6pz)', description: 'Pollo empanizado', price: 8900, emoji: '🍗', category: 'chicken' },
  { id: 18, name: 'Alitas BBQ', description: '6 piezas', price: 12900, emoji: '🍗', category: 'chicken' },
  { id: 19, name: 'Pollo Frito', description: '2 piezas', price: 14900, emoji: '🍗', category: 'chicken' },
  
  // Ensaladas
  { id: 20, name: 'Ensalada César', description: 'Pollo, lechuga, crutones', price: 12900, emoji: '🥗', category: 'salads' },
  { id: 21, name: 'Ensalada Mixta', description: 'Verduras frescas', price: 9900, emoji: '🥗', category: 'salads' }
]

// Estado
const selectedCategory = ref('hot') // Por defecto mostrar "Más Vendidos"
const searchQuery = ref('')
const showCart = ref(false)
// Tipo para items del carrito (pueden ser productos o separadores)
type CartItem = {
  id: string | number
  codigo?: string
  name: string
  price: number
  emoji: string
  quantity: number
  isSeparator?: boolean // Indica si es un separador
  nota?: string // Nota personalizada para el item
}

const cart = ref<Array<CartItem>>([])
const draggedItemIndex = ref<number | null>(null)
const editingNoteIndex = ref<number | null>(null) // Índice del item cuya nota se está editando
const tempNote = ref('') // Nota temporal mientras se edita
const columnsCount = ref<2 | 3>(2) // Número de columnas (2 o 3) - Por defecto: 2

// Modo de teclado (para debug) - Por defecto 'auto'
const keyboardMode = ref<'auto' | 'virtual' | 'hybrid'>('auto')
const showVirtualKeyboard = ref(false)
const activeInput = ref<{ element: HTMLInputElement | null, type: 'numeric' | 'text' | 'email' }>({ element: null, type: 'text' })
const isShiftActive = ref(false) // Estado para mayúsculas/minúsculas

// Flujo de pedido
const showOrderTypeModal = ref(true) // Mostrar al inicio
const orderType = ref<'takeaway' | 'dinein' | null>(null)
const showMesaModal = ref(false) // Modal para número de mesa (solo si es dinein)
const mesaNumber = ref('') // Número de mesa

// Factura electrónica - Flujo en 4 pasos
const showInvoiceModal = ref(false) // Paso 1: ¿A nombre propio o consumidor final?
const showDocumentModal = ref(false) // Paso 2: Tipo documento y número (solo si es a nombre propio)
const showCompleteDataModal = ref(false) // Paso 3: Formulario completo (solo si es a nombre propio)
const showPaymentModal = ref(false) // Paso 4: Continúa en datafono
const showTelefonoConsumidorModal = ref(false) // Modal para pedir teléfono de consumidor final
const showTelefonoPropioModal = ref(false) // Modal para pedir teléfono si no tiene (a nombre propio)
const showFormaPagoModal = ref(false) // Modal para seleccionar forma de pago
const telefonoConsumidor = ref('') // Teléfono para consumidor final
const telefonoPropio = ref('') // Teléfono si no tiene (a nombre propio)
const formasPago = ref<Array<{codigo: string, descripcion: string}>>([]) // Formas de pago disponibles
const notasRapidas = ref<Array<{id: number, texto: string, categorias: string[]}>>([]) // Notas rápidas disponibles
const loadingNotasRapidas = ref(false) // Estado de carga de notas rápidas

// Watch para abrir teclado virtual cuando se muestra modal de teléfono
watch(showTelefonoConsumidorModal, async (isOpen) => {
  if (isOpen && shouldUseVirtualKeyboard('numeric')) {
    await nextTick()
    setTimeout(() => {
      const input = document.querySelector('.telefono-input-hidden') as HTMLInputElement
      if (input) {
        console.log('[VirtualKeyboard] Abriendo teclado para teléfono consumidor')
        openVirtualKeyboard(input, 'numeric')
      }
    }, 300)
  }
})

watch(showTelefonoPropioModal, async (isOpen) => {
  if (isOpen && shouldUseVirtualKeyboard('numeric')) {
    await nextTick()
    setTimeout(() => {
      const inputs = document.querySelectorAll('.telefono-input-hidden')
      const input = inputs[inputs.length - 1] as HTMLInputElement
      if (input) {
        console.log('[VirtualKeyboard] Abriendo teclado para teléfono propio')
        openVirtualKeyboard(input, 'numeric')
      }
    }, 300)
  }
})

// Watch para abrir teclado virtual cuando se abre modal de admin
watch(showUserSwitchModal, async (isOpen) => {
  if (isOpen && !isAdmin.value && shouldUseVirtualKeyboard('text')) {
    await nextTick()
    setTimeout(() => {
      const input = document.querySelector('.password-input-hidden') as HTMLInputElement
      if (input) {
        console.log('[VirtualKeyboard] Abriendo teclado para contraseña admin')
        openVirtualKeyboard(input, 'text')
      }
    }, 300)
  }
})

// Watch para abrir teclado virtual cuando se abre modal de mesa
watch(showMesaModal, async (isOpen) => {
  if (isOpen && shouldUseVirtualKeyboard('numeric')) {
    await nextTick()
    setTimeout(() => {
      const input = document.querySelector('.mesa-input-hidden') as HTMLInputElement
      if (input) {
        console.log('[VirtualKeyboard] Abriendo teclado para mesa')
        openVirtualKeyboard(input, 'numeric')
      }
    }, 300)
  }
})

const formaPagoSeleccionada = ref<string | null>(null) // Código de forma de pago seleccionada
const loadingFormasPago = ref(false)
const wantsInvoice = ref<'propio' | 'consumidor' | null>(null)
const isValidatingDocument = ref(false)
const validatedData = ref<any>({}) // Datos obtenidos de la API de validación
const invoiceData = ref({
  docType: 'cedula' as 'cedula' | 'nit',
  nature: 'natural' as 'natural' | 'juridica',
  document: '',
  name: '',
  email: '',
  phone: ''
})

// Modal de PDF después del pago
const showInvoicePdfModal = ref(false)
const invoicePdfUrl = ref<string | null>(null) // PDF completo para preview
const ticketPdfUrl = ref<string | null>(null) // PDF ticket corto para preview
const pdfCompletoBlob = ref<Blob | null>(null) // Blob del PDF completo para imprimir
const ticketCortoBlob = ref<Blob | null>(null) // Blob del ticket corto para imprimir
const currentKardexId = ref<number | null>(null)
const currentEmpresaId = ref<number | null>(null)
const isGeneratingPdf = ref(false)
const pdfCompletoDisponible = ref(false) // Indica si el PDF completo ya está disponible (con CUFE de DIAN)
const pdfTabActiva = ref<'corto' | 'completo'>('corto') // Pestaña activa en el modal

// Estados para edición de branding (solo ADMIN)
const showBrandingModal = ref(false)
const showGrupoImageModal = ref(false)
const showMaterialImageModal = ref(false)
const showCajaConfigModal = ref(false)
const editingGrupo = ref<string | null>(null)
const editingGrupoDescrip = ref<string | null>(null) // Descripción de la categoría que se está editando
const editingMaterial = ref<string | null>(null)
const notasRapidasCategoria = ref<Array<{id: number, texto: string, categorias: string[], orden: number, activo: boolean}>>([])
const nuevaNotaRapidaTexto = ref('')
const editandoNotaRapida = ref<{id: number, texto: string} | null>(null)
const notaEnEdicion = ref<number | null>(null) // ID de la nota que está en modo edición (mostrando botones)

// Watch para abrir teclado virtual cuando se abre modal de edición de categoría y se enfoca el input de notas rápidas
watch(showGrupoImageModal, async (isOpen) => {
  // El teclado se abre automáticamente cuando el usuario hace click o focus en el input
  // gracias a los handlers @click y @focus
})

const currentCaja = ref<any>(null) // Caja autopago configurada
const cajaConfig = ref({
  nombre: '',
  ip_datafono: '',
  puerto_datafono: 8080,
  modo_mock: true,
  probabilidad_exito: 0.8,
  modo_mock_dian: true,
  activa: true
})
const brandingData = ref({
  logo: null as File | null,
  color_primario: '#DC2626',
  color_secundario: '#FBBF24',
  color_fondo: '#f5f5f5',
  video_por_defecto: null as File | null,
  video_lunes: null as File | null,
  video_martes: null as File | null,
  video_miercoles: null as File | null,
  video_jueves: null as File | null,
  video_viernes: null as File | null,
  video_sabado: null as File | null,
  video_domingo: null as File | null
})
const uploadingImage = ref(false)
const currentBranding = ref({
  logo_url: null as string | null,
  color_primario: '#DC2626',
  color_secundario: '#FBBF24',
  color_fondo: '#f5f5f5',
  modo_teclado: 'auto' as 'auto' | 'virtual' | 'hybrid',
  modo_visualizacion: 'vertical' as 'vertical' | 'horizontal', // 'vertical' = comida, 'horizontal' = otros
  video_por_defecto_url: null as string | null,
  video_del_dia_url: null as string | null
})
const currentGrupoImage = ref<string | null>(null)
const currentMaterialImage = ref<string | null>(null)
const selectedTheme = ref<string>('')

// Modal de vista de producto
const showProductViewModal = ref(false)
const viewingProduct = ref<any>(null)
const productMaterialData = ref<any>(null) // Datos del material (imagen, características, etc.)

// Datos para edición de material
const materialEditData = ref({
  caracteristicas: ''
})

// Protector de Pantalla (Screensaver)
const showScreensaver = ref(false)
const screensaverVideo = ref<HTMLVideoElement | null>(null)
const currentVideoUrl = ref<string | null>(null)
const inactivityTimer = ref<NodeJS.Timeout | null>(null)
const videoCache = ref<Map<string, string>>(new Map()) // Cache de videos: URL -> blob URL
const videoSequence = ref<string[]>([]) // Secuencia de videos a reproducir
const currentVideoIndex = ref(0)
const INACTIVITY_TIMEOUT = 60000 // 1 minuto en milisegundos

// Temas predefinidos
const themes = {
  mcdonalds: {
    color_primario: '#DC2626',
    color_secundario: '#FBBF24',
    color_fondo: '#f5f5f5'
  },
  burgerking: {
    color_primario: '#FF6B35',
    color_secundario: '#F7B801',
    color_fondo: '#f5f5f5'
  },
  frisby: {
    color_primario: '#1E40AF',
    color_secundario: '#FBBF24',
    color_fondo: '#f0f9ff'
  },
  natural: {
    color_primario: '#059669',
    color_secundario: '#FBBF24',
    color_fondo: '#f0fdf4'
  },
  profesional: {
    color_primario: '#1E3A8A',
    color_secundario: '#64748B',
    color_fondo: '#f8fafc'
  }
}

const applyTheme = () => {
  if (selectedTheme.value && themes[selectedTheme.value as keyof typeof themes]) {
    const theme = themes[selectedTheme.value as keyof typeof themes]
    brandingData.value.color_primario = theme.color_primario
    brandingData.value.color_secundario = theme.color_secundario
    brandingData.value.color_fondo = theme.color_fondo
  }
}

// Computed
// Productos filtrados: cuando hay búsqueda, recargar desde backend
const filteredProducts = ref<typeof products.value>([])
const loadingSearch = ref(false)

// Función para cargar productos con filtro de búsqueda
const loadProductsWithSearch = async (searchText?: string) => {
  const empresaId = session.selectedEmpresa.value?.empresaServidorId
  if (!empresaId) {
    filteredProducts.value = products.value.length > 0 ? products.value : mockProducts
    return
  }

  const config = getConfig('materialprecio')
  if (!config) {
    filteredProducts.value = products.value.length > 0 ? products.value : mockProducts
    return
  }

  // Construir filtros
  const filters: any = {
    // Siempre filtrar solo productos con PRECIO1 > 0
    PRECIO1: { operator: '>', value: 0 }
  }
  
  // Si hay búsqueda, filtrar por DESCRIP usando contains (como lo hace el back)
  if (searchText && searchText.trim()) {
    filters.DESCRIP = { contains: searchText.trim() }
  }
  
  // Si hay categoría seleccionada, filtrar por GM_CODIGO (código del grupo)
  // Si es "hot" (Más Vendidos), cargar productos más vendidos directamente
  if (selectedCategory.value === 'hot') {
    // Cargar productos más vendidos
    await loadMasVendidos()
    return
  }
  
  if (selectedCategory.value !== 'all') {
    const selectedCat = categories.value.find(c => c.id === selectedCategory.value)
    if (selectedCat && selectedCat.id !== 'all' && selectedCat.gm_codigo) {
      // Usar el código del grupo (GM_CODIGO) para filtrar
      filters.GM_CODIGO = { operator: '=', value: selectedCat.gm_codigo }
    } else if (selectedCat && selectedCat.gm_descrip) {
      // Fallback: usar descripción si no hay código
      filters.GM_DESCRIP = { contains: selectedCat.gm_descrip }
    }
  }

  try {
    loadingSearch.value = true
    const response = await fetchRecords(config, {
      empresa_servidor_id: empresaId,
      page: 1,
      page_size: 200,
      order_by: [{ field: 'CODIGO', direction: 'ASC' }],
      filters: Object.keys(filters).length > 0 ? filters : undefined
    })

    // Procesar productos igual que en loadProducts
    const productsMap = new Map<string, any>()
    for (const row of response.data) {
      const codigo = row.CODIGO || row.codigo
      if (!codigo) continue

      if (!productsMap.has(codigo)) {
        productsMap.set(codigo, {
          codigo,
          codbarra: row.CODBARRA || row.codbarra,
          name: row.DESCRIP || row.descrip || codigo,
          description: `${row.UNIDAD || ''} ${row.PESO ? `(${row.PESO} kg)` : ''}`.trim() || codigo,
          price: parseFloat(row.PRECIO1 || row.precio1 || 0) || 0, // Precio por defecto: PRECIO1
          stock: undefined,
          peso: row.PESO || row.peso,
          unidad: row.UNIDAD || row.unidad,
          gm_codigo: row.GM_CODIGO || row.gm_codigo,
          gm_descrip: row.GM_DESCRIP || row.gm_descrip,
          gc_codigo: row.GC_CODIGO || row.gc_codigo,
          gc_descrip: row.GC_DESCRIP || row.gc_descrip,
          costo: parseFloat(row.COSTO || row.costo || 0) || 0,
          precio1: parseFloat(row.PRECIO1 || row.precio1 || 0) || 0,
          precio2: parseFloat(row.PRECIO2 || row.precio2 || 0) || 0,
          precio3: parseFloat(row.PRECIO3 || row.precio3 || 0) || 0,
          precio4: parseFloat(row.PRECIO4 || row.precio4 || 0) || 0,
          precio5: parseFloat(row.PRECIO5 || row.precio5 || 0) || 0,
          imagen_url: row.imagen_url || null, // URL de imagen del material
          grupo_imagen_url: row.grupo_imagen_url || null, // URL de imagen del grupo
          caracteristicas: row.caracteristicas || null // Características del material
        })
      }
    }

    // Mapear a formato del componente (igual que loadProducts)
    filteredProducts.value = Array.from(productsMap.values()).map((p) => {
      const categoryName = (p.gm_descrip || '').toLowerCase()
      let emoji = '📦'
      let category = 'otros'
      
      if (categoryName.includes('bebida') || categoryName.includes('refresco') || categoryName.includes('agua')) {
        emoji = '🥤'
        category = 'drinks'
      } else if (categoryName.includes('hamburguesa') || categoryName.includes('burger') || categoryName.includes('carne')) {
        emoji = '🍔'
        category = 'burgers'
      } else if (categoryName.includes('papa') || categoryName.includes('frita') || categoryName.includes('snack')) {
        emoji = '🍟'
        category = 'fries'
      } else if (categoryName.includes('postre') || categoryName.includes('helado') || categoryName.includes('dulce')) {
        emoji = '🍰'
        category = 'desserts'
      } else if (categoryName.includes('pollo') || categoryName.includes('chicken') || categoryName.includes('nugget')) {
        emoji = '🍗'
        category = 'chicken'
      } else if (categoryName.includes('ensalada') || categoryName.includes('salad') || categoryName.includes('verdura')) {
        emoji = '🥗'
        category = 'salads'
      }

      return {
        ...p,
        emoji,
        category,
        imagen_url: p.imagen_url || null, // Preservar imagen_url
        grupo_imagen_url: p.grupo_imagen_url || null // Preservar grupo_imagen_url
      }
    })
  } catch (error) {
    console.error('[retail] Error en búsqueda:', error)
    filteredProducts.value = products.value.length > 0 ? products.value : mockProducts
  } finally {
    loadingSearch.value = false
  }
}

// Watch para búsqueda y categoría
watch([searchQuery, selectedCategory], async ([newSearch, newCategory]) => {
  // Si hay búsqueda, siempre usar búsqueda (ignorar categoría)
  if (newSearch && newSearch.trim()) {
    await loadProductsWithSearch(newSearch)
    return
  }
  
  // Si se selecciona categoría "hot" (Más Vendidos), cargar productos más vendidos
  if (newCategory === 'hot') {
    await loadMasVendidos()
    return
  }
  
  // Para otras categorías, filtrar desde products.value en memoria (instantáneo, sin API)
  if (newCategory && newCategory !== 'hot' && products.value.length > 0) {
    const selectedCat = categories.value.find(c => c.id === newCategory)
    if (selectedCat && selectedCat.gm_codigo) {
      // Filtrar por código de grupo desde productos en memoria (instantáneo)
      filteredProducts.value = products.value.filter(p => p.gm_codigo === selectedCat.gm_codigo)
      console.log(`[retail] ✅ Categoría "${selectedCat.name}" filtrada instantáneamente: ${filteredProducts.value.length} productos`)
      return
    } else if (selectedCat && selectedCat.gm_descrip) {
      // Filtrar por descripción desde productos en memoria (instantáneo)
      filteredProducts.value = products.value.filter(p => 
        (p.gm_descrip || '').toLowerCase().includes(selectedCat.gm_descrip.toLowerCase())
      )
      console.log(`[retail] ✅ Categoría "${selectedCat.name}" filtrada instantáneamente: ${filteredProducts.value.length} productos`)
      return
    }
  }
  
  // Si no hay filtros, mostrar todos los productos
  if (!newCategory || newCategory === 'all') {
    filteredProducts.value = products.value
  }
}, { immediate: false }) // No ejecutar inmediatamente para evitar llamadas innecesarias

// Categorías: cargar todos los grupos de GRUPMAT
const allGroups = ref<Array<{ codigo: string, descrip: string }>>([])
// Función para cargar productos más vendidos usando records
const loadingMasVendidos = ref(false)
const loadMasVendidos = async () => {
  const empresaId = session.selectedEmpresa.value?.empresaServidorId
  if (!empresaId) {
    console.warn('[retail] No hay empresa seleccionada para cargar más vendidos')
    return
  }

  loadingMasVendidos.value = true
  try {
    console.log('[retail] Cargando productos más vendidos...')
    
    // Usar el endpoint records con foreign_keys para hacer los JOINs
    const response = await fetchRecords({
      tableName: 'DEKARDEX',
      primaryKey: 'DEKARDEXID',
      apiEndpoint: '/api/tns/records/',
      fields: [
        { name: 'MATID' },
        { name: 'KARDEXID' },
        // Incluir campos de foreign keys para que se devuelvan en la respuesta
        { name: 'CODIGO' },      // De MATERIAL
        { name: 'DESCRIP' },     // De MATERIAL
        { name: 'UNIDAD' },      // De MATERIAL
        { name: 'PESO' },        // De MATERIAL
        { name: 'CODBARRA' },    // De MATERIAL
        { name: 'GM_CODIGO' },   // De GRUPMAT
        { name: 'GM_DESCRIP' },  // De GRUPMAT
        { name: 'PRECIO1' }      // De MATERIALSUC
      ],
      foreignKeys: [
        {
          table: 'KARDEX',
          localField: 'KARDEXID',
          foreignField: 'KARDEXID',
          columns: [
            { name: 'FECHA', as: 'KARDEX_FECHA' }
          ]
        },
        {
          table: 'MATERIAL',
          localField: 'MATID',
          foreignField: 'MATID',
          columns: [
            { name: 'CODIGO', as: 'CODIGO' },
            { name: 'DESCRIP', as: 'DESCRIP' },
            { name: 'UNIDAD', as: 'UNIDAD' },
            { name: 'PESO', as: 'PESO' },
            { name: 'CODBARRA', as: 'CODBARRA' },
            { name: 'GRUPMATID', as: 'GRUPMATID' }
          ]
        },
        {
          table: 'GRUPMAT',
          localField: 'GRUPMATID',
          foreignField: 'GRUPMATID',
          joinFrom: 'MATERIAL',
          columns: [
            { name: 'DESCRIP', as: 'GM_DESCRIP' },
            { name: 'CODIGO', as: 'GM_CODIGO' }
          ]
        },
        {
          table: 'MATERIALSUC',
          localField: 'MATID',
          foreignField: 'MATID',
          joinFrom: 'MATERIAL',
          columns: [
            { name: 'PRECIO1', as: 'PRECIO1' }
          ]
        }
      ],
      searchFields: []
    }, {
      empresa_servidor_id: empresaId,
      filters: {
        // Filtrar por fecha de los últimos 30 días
        // Usar formato TABLA_CAMPO para que el query builder lo detecte como FK
        KARDEX_FECHA: {
          between: [
            // Fecha de hace 30 días (formato YYYY-MM-DD)
            new Date(Date.now() - 30 * 24 * 60 * 60 * 1000).toISOString().split('T')[0],
            // Fecha de hoy (formato YYYY-MM-DD)
            new Date().toISOString().split('T')[0]
          ]
        },
        PRECIO1: { operator: '>', value: 1000 }
      },
      order_by: [
        { field: 'PRECIO1', direction: 'DESC' }
      ],
      page: 1,
      page_size: 500 // Aumentar para obtener más productos
    })

    console.log('[retail] Productos más vendidos recibidos:', response.data?.length || 0)
    console.log('[retail] Datos recibidos (primeros 3):', response.data?.slice(0, 3))

    // Si no hay resultados con filtro de fecha, intentar sin filtro de fecha
    if (!response.data || response.data.length === 0) {
      console.warn('[retail] No se encontraron productos más vendidos con filtro de fecha, intentando sin filtro de fecha...')
      
      try {
        const responseSinFecha = await fetchRecords({
          tableName: 'DEKARDEX',
          primaryKey: 'DEKARDEXID',
          apiEndpoint: '/api/tns/records/',
          fields: [
            { name: 'MATID' },
            { name: 'KARDEXID' },
            // Incluir campos de foreign keys para que se devuelvan en la respuesta
            { name: 'CODIGO' },      // De MATERIAL
            { name: 'DESCRIP' },     // De MATERIAL
            { name: 'UNIDAD' },      // De MATERIAL
            { name: 'PESO' },        // De MATERIAL
            { name: 'CODBARRA' },    // De MATERIAL
            { name: 'GM_CODIGO' },   // De GRUPMAT
            { name: 'GM_DESCRIP' },  // De GRUPMAT
            { name: 'PRECIO1' }      // De MATERIALSUC
          ],
          foreignKeys: [
            {
              table: 'KARDEX',
              localField: 'KARDEXID',
              foreignField: 'KARDEXID',
              columns: [
                { name: 'FECHA', as: 'KARDEX_FECHA' }
              ]
            },
            {
              table: 'MATERIAL',
              localField: 'MATID',
              foreignField: 'MATID',
              columns: [
                { name: 'CODIGO', as: 'CODIGO' },
                { name: 'DESCRIP', as: 'DESCRIP' },
                { name: 'UNIDAD', as: 'UNIDAD' },
                { name: 'PESO', as: 'PESO' },
                { name: 'CODBARRA', as: 'CODBARRA' },
                { name: 'GRUPMATID', as: 'GRUPMATID' }
              ]
            },
            {
              table: 'GRUPMAT',
              localField: 'GRUPMATID',
              foreignField: 'GRUPMATID',
              joinFrom: 'MATERIAL',
              columns: [
                { name: 'DESCRIP', as: 'GM_DESCRIP' },
                { name: 'CODIGO', as: 'GM_CODIGO' }
              ]
            },
            {
              table: 'MATERIALSUC',
              localField: 'MATID',
              foreignField: 'MATID',
              joinFrom: 'MATERIAL',
              columns: [
                { name: 'PRECIO1', as: 'PRECIO1' }
              ]
            }
          ],
          searchFields: []
        }, {
          empresa_servidor_id: empresaId,
          filters: {
            PRECIO1: { operator: '>', value: 1000 }
          },
          order_by: [
            { field: 'PRECIO1', direction: 'DESC' }
          ],
          page: 1,
          page_size: 500 // Aumentar para obtener más productos
        })
        
        if (responseSinFecha.data && responseSinFecha.data.length > 0) {
          console.log('[retail] Productos encontrados sin filtro de fecha:', responseSinFecha.data.length)
          response.data = responseSinFecha.data
        } else {
          console.warn('[retail] No se encontraron productos más vendidos, mostrando todos los productos')
          if (products.value.length > 0) {
            filteredProducts.value = products.value
          }
          return
        }
      } catch (errorSinFecha: any) {
        console.error('[retail] Error cargando productos sin filtro de fecha:', errorSinFecha)
        if (products.value.length > 0) {
          filteredProducts.value = products.value
        }
        return
      }
    }

    // Procesar productos: agrupar por código y contar frecuencia
    const productsMap = new Map<string, { product: any, count: number }>()
    
    for (const row of response.data) {
      const codigo = row.CODIGO || row.codigo
      if (!codigo) continue

      if (productsMap.has(codigo)) {
        // Incrementar contador si ya existe
        productsMap.get(codigo)!.count++
      } else {
        // Crear nuevo producto
        productsMap.set(codigo, {
          count: 1,
          product: {
            codigo,
            codbarra: row.CODBARRA || row.codbarra,
            name: row.DESCRIP || row.descrip || codigo,
            description: `${row.UNIDAD || ''} ${row.PESO ? `(${row.PESO} kg)` : ''}`.trim() || codigo,
            price: parseFloat(row.PRECIO1 || row.precio1 || 0) || 0,
            stock: undefined,
            peso: row.PESO || row.peso,
            unidad: row.UNIDAD || row.unidad,
            gm_codigo: row.GM_CODIGO || row.gm_codigo,
            gm_descrip: row.GM_DESCRIP || row.GRUPO_DESCRIP || row.gm_descrip,
            imagen_url: null, // Los productos más vendidos no tienen imagen por defecto
            grupo_imagen_url: null
          }
        })
      }
    }
    
    // Convertir a array y ordenar por frecuencia (más vendidos primero)
    const sortedProducts = Array.from(productsMap.values())
      .sort((a, b) => b.count - a.count) // Ordenar por frecuencia descendente
      .map(item => item.product)
    
    // Asegurar al menos 50 productos (si hay menos, completar con productos de products.value)
    let finalProducts = sortedProducts
    if (sortedProducts.length < 50 && products.value.length > 0) {
      // Agregar productos de products.value que no estén ya en sortedProducts
      const existingCodes = new Set(sortedProducts.map(p => p.codigo))
      const additionalProducts = products.value
        .filter(p => p.codigo && !existingCodes.has(p.codigo))
        .slice(0, 50 - sortedProducts.length)
      finalProducts = [...sortedProducts, ...additionalProducts]
      console.log(`[retail] Completando más vendidos: ${sortedProducts.length} + ${additionalProducts.length} = ${finalProducts.length} productos`)
    }
    
    // Limitar a máximo 50 productos
    finalProducts = finalProducts.slice(0, 50)

    // Mapear a formato del componente
    const processedProducts = finalProducts.map((p) => {
      const categoryName = (p.gm_descrip || '').toLowerCase()
      let emoji = '🔥' // Default para más vendidos
      let category = 'hot'
      
      if (categoryName.includes('bebida') || categoryName.includes('refresco') || categoryName.includes('agua')) {
        emoji = '🥤'
        category = 'drinks'
      } else if (categoryName.includes('hamburguesa') || categoryName.includes('burger') || categoryName.includes('carne')) {
        emoji = '🍔'
        category = 'burgers'
      } else if (categoryName.includes('papa') || categoryName.includes('frita') || categoryName.includes('snack')) {
        emoji = '🍟'
        category = 'fries'
      } else if (categoryName.includes('postre') || categoryName.includes('helado') || categoryName.includes('dulce')) {
        emoji = '🍦'
        category = 'desserts'
      } else if (categoryName.includes('pollo') || categoryName.includes('chicken') || categoryName.includes('nugget')) {
        emoji = '🍗'
        category = 'chicken'
      } else if (categoryName.includes('ensalada') || categoryName.includes('salad')) {
        emoji = '🥗'
        category = 'salads'
      }

      return {
        id: p.codigo,
        name: p.name,
        description: p.description,
        price: p.price,
        emoji,
        category,
        stock: p.stock,
        codigo: p.codigo,
        codbarra: p.codbarra,
        peso: p.peso,
        unidad: p.unidad,
        gm_codigo: p.gm_codigo,
        gm_descrip: p.gm_descrip,
        imagen_url: p.imagen_url || null,
        grupo_imagen_url: p.grupo_imagen_url || null
      }
    })

    filteredProducts.value = processedProducts
    console.log(`[retail] ✅ Productos más vendidos cargados: ${processedProducts.length} productos (mínimo 50 garantizado)`)
    
  } catch (error: any) {
    console.error('[retail] Error cargando productos más vendidos:', error)
    // Si hay error, mantener los productos existentes en lugar de vaciar
    if (products.value.length > 0) {
      filteredProducts.value = products.value
    }
  } finally {
    loadingMasVendidos.value = false
  }
}

// Computed properties para modo de visualización
const modoVisualizacion = computed(() => {
  return currentBranding.value?.modo_visualizacion || 'vertical'
})

const esModoComida = computed(() => modoVisualizacion.value === 'vertical')
const esModoHorizontal = computed(() => modoVisualizacion.value === 'horizontal')

const categories = computed(() => {
  // Categorías base siempre presentes (ocultar "Todos")
  const baseCategories = [
    { id: 'hot', name: 'Más Vendidos', icon: '🔥', gm_codigo: null, gm_descrip: null, imagen_url: null }
  ]
  
  // Mapear grupos de GRUPMAT a categorías
  const categoryMap: Record<string, { name: string, icon: string }> = {
    burgers: { name: 'Hamburguesas', icon: '🍔' },
    drinks: { name: 'Bebidas', icon: '🥤' },
    fries: { name: 'Papas', icon: '🍟' },
    desserts: { name: 'Postres', icon: '🍰' },
    chicken: { name: 'Pollo', icon: '🍗' },
    salads: { name: 'Ensaladas', icon: '🥗' },
    otros: { name: 'Otros', icon: '📦' }
  }
  
  // Crear categorías desde todos los grupos de GRUPMAT
  const groupCategories = allGroups.value.map(group => {
    const descripLower = (group.descrip || '').toLowerCase()
    let categoryId = 'otros'
    let icon = '📦'
    
    // Determinar categoría según descripción
    if (descripLower.includes('bebida') || descripLower.includes('refresco') || descripLower.includes('agua')) {
      categoryId = 'drinks'
      icon = '🥤'
    } else if (descripLower.includes('hamburguesa') || descripLower.includes('burger') || descripLower.includes('carne')) {
      categoryId = 'burgers'
      icon = '🍔'
    } else if (descripLower.includes('papa') || descripLower.includes('frita') || descripLower.includes('snack')) {
      categoryId = 'fries'
      icon = '🍟'
    } else if (descripLower.includes('postre') || descripLower.includes('helado') || descripLower.includes('dulce')) {
      categoryId = 'desserts'
      icon = '🍰'
    } else if (descripLower.includes('pollo') || descripLower.includes('chicken') || descripLower.includes('nugget')) {
      categoryId = 'chicken'
      icon = '🍗'
    } else if (descripLower.includes('ensalada') || descripLower.includes('salad') || descripLower.includes('verdura')) {
      categoryId = 'salads'
      icon = '🥗'
    }
    
      return {
        id: group.codigo || categoryId,
        name: group.descrip || categoryMap[categoryId]?.name || 'Otros',
        icon: categoryMap[categoryId]?.icon || icon,
        gm_codigo: group.codigo, // Código del grupo para filtrar
        gm_descrip: group.descrip, // Descripción del grupo
        imagen_url: group.imagen_url || null // URL de imagen del grupo (si existe)
      }
  })
  
  return [...baseCategories, ...groupCategories]
})

const cartTotalItems = computed(() => {
  return cart.value
    .filter(item => !item.isSeparator)
    .reduce((sum, item) => sum + item.quantity, 0)
})

const cartSubtotal = computed(() => {
  return cart.value
    .filter(item => !item.isSeparator)
    .reduce((sum, item) => sum + (item.price * item.quantity), 0)
})

const cartTotal = computed(() => {
  return cartSubtotal.value
})

// Métodos
const formatPrice = (price: number) => {
  return new Intl.NumberFormat('es-CO').format(price)
}

const addToCart = (product: typeof mockProducts[0]) => {
  // Usar código como identificador único (es el identificador real en TNS)
  const productCodigo = product.codigo
  if (!productCodigo) {
    console.error('[addToCart] Producto sin código:', product)
    return
  }
  
  // Buscar si ya existe un producto con el mismo código en el carrito
  const existingItem = cart.value.find(item => item.codigo === productCodigo)
  
  if (existingItem) {
    // Si ya existe, aumentar cantidad
    existingItem.quantity++
    console.log(`[addToCart] Producto existente: ${product.name} (código: ${productCodigo}), nueva cantidad: ${existingItem.quantity}`)
  } else {
    // Si no existe, agregar como nuevo item
    cart.value.push({
      id: product.id || productCodigo,
      codigo: productCodigo, // Código es obligatorio
      name: product.name,
      price: product.price,
      emoji: product.emoji,
      quantity: 1
    })
    console.log(`[addToCart] Nuevo producto agregado: ${product.name} (código: ${productCodigo})`)
  }
  
  // Mostrar carrito automáticamente
  showCart.value = true
}

const increaseQuantity = (index: number) => {
  cart.value[index].quantity++
}

const decreaseQuantity = (index: number) => {
  if (cart.value[index].quantity > 1) {
    cart.value[index].quantity--
  } else {
    removeFromCart(index)
  }
}

const removeFromCart = (index: number) => {
  cart.value.splice(index, 1)
  if (cart.value.length === 0) {
    showCart.value = false
  }
}

// Funciones para drag and drop
const handleDragStart = (index: number, event: DragEvent) => {
  draggedItemIndex.value = index
  if (event.dataTransfer) {
    event.dataTransfer.effectAllowed = 'move'
    event.dataTransfer.setData('text/html', '')
  }
}

const handleDragEnd = () => {
  draggedItemIndex.value = null
}

const handleDragOver = (index: number, event: DragEvent) => {
  event.preventDefault()
  if (event.dataTransfer) {
    event.dataTransfer.dropEffect = 'move'
  }
}

const handleDrop = (targetIndex: number, event: DragEvent) => {
  event.preventDefault()
  if (draggedItemIndex.value === null || draggedItemIndex.value === targetIndex) {
    return
  }
  
  const draggedItem = cart.value[draggedItemIndex.value]
  cart.value.splice(draggedItemIndex.value, 1)
  cart.value.splice(targetIndex, 0, draggedItem)
  draggedItemIndex.value = null
}

// Agregar separador al carrito
const addSeparator = () => {
  const separatorId = `separator-${Date.now()}`
  cart.value.push({
    id: separatorId,
    name: 'Separador',
    price: 0,
    emoji: '━━━',
    quantity: 1,
    isSeparator: true
  })
}

// Funciones para editar notas
const openNoteEditor = async (index: number) => {
  // Validar que el índice sea válido y no sea un separador
  if (index < 0 || index >= cart.value.length) {
    console.error('[retail] Índice inválido para editar nota:', index)
    return
  }
  
  const item = cart.value[index]
  if (!item || item.isSeparator) {
    console.warn('[retail] No se puede agregar nota a un separador')
    return
  }
  
  editingNoteIndex.value = index
  tempNote.value = item.nota || ''
  
  // Cargar notas rápidas si no están cargadas
  if (!notasRapidas.value || notasRapidas.value.length === 0) {
    await loadNotasRapidas()
  }
}

const closeNoteEditor = () => {
  editingNoteIndex.value = null
  tempNote.value = ''
  notasRapidasSeleccionadas.value.clear()
}

const saveNote = () => {
  if (editingNoteIndex.value !== null) {
    cart.value[editingNoteIndex.value].nota = tempNote.value.trim()
    closeNoteEditor()
  }
}

// Notas rápidas seleccionadas (para cambiar color de botones)
const notasRapidasSeleccionadas = ref<Set<string>>(new Set())

// Verificar si una nota rápida está activa (seleccionada)
const isNotaRapidaActiva = (texto: string): boolean => {
  // Verificar si el texto está en tempNote
  if (!tempNote.value) return false
  const partes = tempNote.value.split(',').map(p => p.trim())
  return partes.includes(texto.trim())
}

// Toggle nota rápida (agregar o quitar)
const toggleNotaRapida = (notaRapida: {texto: string}) => {
  const texto = notaRapida.texto.trim()
  if (!tempNote.value) {
    tempNote.value = ''
  }
  
  const partes = tempNote.value.split(',').map(p => p.trim()).filter(p => p !== '')
  const yaEstaIncluida = partes.includes(texto)
  
  if (yaEstaIncluida) {
    // Quitar la nota
    const nuevasPartes = partes.filter(p => p !== texto)
    tempNote.value = nuevasPartes.join(', ')
  } else {
    // Agregar la nota
    if (partes.length > 0) {
      tempNote.value += ', ' + texto
    } else {
      tempNote.value = texto
    }
  }
  
  // Actualizar set de seleccionadas
  if (yaEstaIncluida) {
    notasRapidasSeleccionadas.value.delete(texto)
  } else {
    notasRapidasSeleccionadas.value.add(texto)
  }
  
  // Enfocar el textarea para continuar escribiendo
  nextTick(() => {
    const textarea = document.querySelector('.note-textarea') as HTMLTextAreaElement
    if (textarea) {
      textarea.focus()
      textarea.setSelectionRange(textarea.value.length, textarea.value.length)
    }
  })
}

// Agregar nota rápida al texto (función legacy, mantener por compatibilidad)
const agregarNotaRapida = (texto: string) => {
  toggleNotaRapida({ texto })
}

// Computed para notas rápidas disponibles según la categoría del producto
const notasRapidasDisponibles = computed(() => {
  if (editingNoteIndex.value === null) return []
  
  const item = cart.value[editingNoteIndex.value]
  if (!item || item.isSeparator) return []
  
  // Buscar el producto en la lista de productos para obtener su categoría (gm_codigo)
  const producto = products.value.find(p => p.codigo === item.codigo)
  const categoriaCodigo = producto?.gm_codigo
  
  // Filtrar notas rápidas:
  // - Si la nota no tiene categorías asociadas (array vacío), está disponible para todos
  // - Si tiene categorías, debe incluir la categoría del producto
  if (!notasRapidas.value || notasRapidas.value.length === 0) {
    return []
  }
  if (!notasRapidas.value || notasRapidas.value.length === 0) {
    return []
  }
  return notasRapidas.value.filter(nota => {
    if (!nota.categorias || nota.categorias.length === 0) {
      return true // Disponible para todas las categorías
    }
    return categoriaCodigo && nota.categorias.includes(categoriaCodigo)
  })
})

// Cargar notas rápidas desde el backend
const loadNotasRapidas = async () => {
  if (loadingNotasRapidas.value) return
  
  try {
    loadingNotasRapidas.value = true
    const empresaId = session.selectedEmpresa.value?.empresaServidorId
    if (!empresaId) return
    
    const response = await api.get('/api/notas-rapidas/list/', {
      empresa_servidor_id: empresaId,
      activo: true
    })
    
    if (response.data && response.data.success) {
      notasRapidas.value = response.data.data || []
    } else {
      notasRapidas.value = response.data || []
    }
  } catch (error) {
    console.error('Error cargando notas rápidas:', error)
    notasRapidas.value = []
  } finally {
    loadingNotasRapidas.value = false
  }
}

// Generar observaciones agrupadas por separadores
const generarObservacionesAgrupadas = (): string => {
  const grupos: string[] = []
  let grupoActual: string[] = []
  
  for (const item of cart.value) {
    if (item.isSeparator) {
      // Si hay items en el grupo actual, agregarlo
      if (grupoActual.length > 0) {
        grupos.push(`(${grupoActual.join('-')})`)
        grupoActual = []
      }
    } else {
      // Agregar el nombre del item al grupo actual (repetido según cantidad)
      // Si tiene nota, incluirla en el formato: "NOMBRE: NOTA"
      for (let i = 0; i < item.quantity; i++) {
        if (item.nota && item.nota.trim() !== '') {
          grupoActual.push(`${item.name}: ${item.nota.trim()}`)
        } else {
          grupoActual.push(item.name)
        }
      }
    }
  }
  
  // Agregar el último grupo si hay items
  if (grupoActual.length > 0) {
    grupos.push(`(${grupoActual.join('-')})`)
  }
  
  return grupos.join('')
}

// Función para reiniciar todo el ciclo después de una impresión exitosa
const resetearTodo = () => {
  // Limpiar carrito
  cart.value = []
  showCart.value = false
  
  // Limpiar datos de factura
  invoiceData.value = {
    documentType: '',
    documentNumber: '',
    name: '',
    email: '',
    phone: '',
    nature: 'natural'
  }
  validatedData.value = {
    name: '',
    email: '',
    phone: '',
    address: ''
  }
  
  // Limpiar modales
  showInvoicePdfModal.value = false
  showPaymentModal.value = false
  showFormaPagoModal.value = false
  showCompleteDataModal.value = false
  showDocumentModal.value = false
  showInvoiceModal.value = false
  showTelefonoConsumidorModal.value = false
  showTelefonoPropioModal.value = false
  showMesaModal.value = false
  
  // Limpiar datos de pedido
  orderType.value = null
  mesaNumber.value = ''
  telefonoConsumidor.value = ''
  telefonoPropio.value = ''
  formaPagoSeleccionada.value = ''
  wantsInvoice.value = null
  
  // Limpiar PDFs
  pdfCompletoBlob.value = null
  ticketCortoBlob.value = null
  invoicePdfUrl.value = ''
  currentKardexId.value = null
}

// Métodos de flujo
const selectOrderType = (type: 'takeaway' | 'dinein') => {
  orderType.value = type
  showOrderTypeModal.value = false
  
  // Si es para comer aquí, preguntar número de mesa (opcional)
  if (type === 'dinein') {
    // Siempre mostrar modal de mesa para que pueda elegir o seleccionar "Sin Mesa"
    showMesaModal.value = true
  } else {
    // Para llevar: limpiar mesa si había una seleccionada
    mesaNumber.value = ''
  }
}

// En modo horizontal, no mostrar modal inicial
watch(esModoHorizontal, (isHorizontal) => {
  if (isHorizontal && showOrderTypeModal.value) {
    showOrderTypeModal.value = false
    orderType.value = null // No hay tipo de pedido en modo horizontal
  }
}, { immediate: true })

const confirmMesa = () => {
  // Permitir continuar incluso sin mesa (opcional)
  showMesaModal.value = false
}

const selectSinMesa = () => {
  mesaNumber.value = ''
  showMesaModal.value = false
}

const cancelMesaModal = () => {
  showMesaModal.value = false
  // Si no hay mesa seleccionada, volver al modal de tipo de pedido
  if (!mesaNumber.value || mesaNumber.value.trim() === '') {
    orderType.value = null
    showOrderTypeModal.value = true
  }
}

const proceedToCheckout = () => {
  // Paso 1: Mostrar modal preguntando si quiere factura a nombre propio o consumidor final
  showCart.value = false
  showInvoiceModal.value = true
  wantsInvoice.value = null
  // Resetear datos
  invoiceData.value = {
    docType: 'cedula',
    nature: 'natural',
    document: '',
    name: '',
    email: '',
    phone: ''
  }
  validatedData.value = {}
}

const selectInvoiceType = async (type: 'propio' | 'consumidor') => {
  wantsInvoice.value = type
  
  if (type === 'consumidor') {
    // Si es consumidor final, pedir teléfono obligatorio
    showInvoiceModal.value = false
    showTelefonoConsumidorModal.value = true
    // Abrir teclado virtual después de que el modal se muestre
    await nextTick()
    setTimeout(() => {
      const input = document.querySelector('.telefono-input-hidden') as HTMLInputElement
      if (input && shouldUseVirtualKeyboard('numeric')) {
        openVirtualKeyboard(input, 'numeric')
      }
    }, 300)
  } else {
    // Si es a nombre propio, mostrar modal de documento
    showInvoiceModal.value = false
    showDocumentModal.value = true
  }
}

const cancelInvoiceModal = () => {
  showInvoiceModal.value = false
  wantsInvoice.value = null
}

const cancelDocumentModal = () => {
  showDocumentModal.value = false
  invoiceData.value.document = ''
  validatedData.value = {}
  // Volver al modal de tipo de factura
  showInvoiceModal.value = true
}

const goBackToDocumentModal = () => {
  showCompleteDataModal.value = false
  showDocumentModal.value = true
  // Limpiar datos validados pero mantener el documento
  validatedData.value = {}
}

// Helper para mostrar alertas con SweetAlert2
const showAlert = async (
  type: 'success' | 'error' | 'warning' | 'info', 
  title: string, 
  text?: string, 
  timer?: number,
  allowOutsideClick: boolean = true
) => {
  if (!process.client) return
  
  const Swal = (await import('sweetalert2')).default
  const swalConfig: any = {
    icon: type,
    title,
    text,
    confirmButtonText: 'Aceptar',
    confirmButtonColor: type === 'error' ? '#DC2626' : type === 'success' ? '#10B981' : '#2563eb',
    customClass: {
      container: 'swal-z-index-fix'
    },
    allowOutsideClick: allowOutsideClick
  }
  
  // Si se especifica timer, cerrar automáticamente
  if (timer !== undefined) {
    if (timer === 0) {
      // Timer 0 = no cerrar automáticamente, mostrar loader
      swalConfig.showConfirmButton = false
      swalConfig.allowOutsideClick = false
      swalConfig.didOpen = () => {
        Swal.showLoading()
      }
    } else {
      swalConfig.timer = timer
      swalConfig.timerProgressBar = true
    }
  }
  
  await Swal.fire(swalConfig)
}

const validateDocument = async () => {
  if (!invoiceData.value.document || invoiceData.value.document.length < 7) {
    return
  }

  if (!session.selectedEmpresa.value) {
    await showAlert('error', 'Error', 'No hay empresa seleccionada')
    return
  }

  isValidatingDocument.value = true

  try {
    const empresaId = session.selectedEmpresa.value.empresaServidorId
    
    // Llamar API de validación de tercero
    const response = await api.post('/api/tns/validar-tercero/', {
      empresa_servidor_id: empresaId,
      document_type: invoiceData.value.docType, // 'cedula' o 'nit'
      document_number: invoiceData.value.document
    })

    // Si se encontró en TNS, usar esos datos directamente
    if (response.encontrado_en_tns) {
      validatedData.value = {
        name: response.nombre || '',
        email: response.email || '',
        telefono: response.telefono || '',
        nit: response.nit || invoiceData.value.document
      }
      
      // Prellenar campos del formulario
      if (response.nombre) {
        invoiceData.value.name = response.nombre
      }
      if (response.email) {
        invoiceData.value.email = response.email
      }
      if (response.telefono) {
        invoiceData.value.phone = response.telefono
      }
      
      // Determinar naturaleza según tipo de documento
      if (invoiceData.value.docType === 'nit') {
        invoiceData.value.nature = 'juridica'
      } else {
        invoiceData.value.nature = 'natural'
      }
      
      // Cerrar modal de documento y abrir modal de datos completos
      showDocumentModal.value = false
      showCompleteDataModal.value = true
    } else if (response.encontrado_en_dian) {
      // Se encontró en DIAN pero no en TNS - prellenar datos y pasar al formulario
      validatedData.value = {
        name: response.nombre || '',
        email: response.email || '',
        telefono: response.telefono || '',
        nit: response.nit || invoiceData.value.document
      }
      
      // Prellenar campos del formulario con datos de DIAN
      if (response.nombre) {
        invoiceData.value.name = response.nombre
      }
      if (response.email) {
        invoiceData.value.email = response.email
      }
      if (response.telefono) {
        invoiceData.value.phone = response.telefono
      }
      
      // Determinar naturaleza según tipo de documento
      if (invoiceData.value.docType === 'nit') {
        invoiceData.value.nature = 'juridica'
      } else {
        invoiceData.value.nature = 'natural'
      }
      
      // Cerrar modal de documento y abrir modal de datos completos
      // El usuario completará el formulario y ahí se creará el tercero en TNS
      showDocumentModal.value = false
      showCompleteDataModal.value = true
    } else {
      // No se encontró en ningún lado
      await showAlert('warning', 'Documento no encontrado', 'No se encontró información para este documento. Por favor, completa los datos manualmente.')
      
      // Determinar naturaleza según tipo de documento
      if (invoiceData.value.docType === 'nit') {
        invoiceData.value.nature = 'juridica'
      } else {
        invoiceData.value.nature = 'natural'
      }
      
      // Abrir modal de datos completos para llenar manualmente
      showDocumentModal.value = false
      showCompleteDataModal.value = true
    }
  } catch (error: any) {
    console.error('Error validando documento:', error)
    const errorMsg = error?.data?.error || error?.message || 'Error al validar documento'
    await showAlert('error', 'Error al validar documento', errorMsg)
    
    // Aún así, permitir continuar manualmente
    if (invoiceData.value.docType === 'nit') {
      invoiceData.value.nature = 'juridica'
    } else {
      invoiceData.value.nature = 'natural'
    }
    showDocumentModal.value = false
    showCompleteDataModal.value = true
  } finally {
    isValidatingDocument.value = false
  }
}

// Funciones para modales de teléfono y forma de pago
const confirmTelefonoConsumidor = async () => {
  if (!telefonoConsumidor.value || telefonoConsumidor.value.length !== 10 || !telefonoConsumidor.value.startsWith('3')) {
    await showAlert('warning', 'Teléfono inválido', 'El teléfono debe empezar por 3 y tener 10 dígitos')
    return
  }
  showTelefonoConsumidorModal.value = false
  // Guardar teléfono en invoiceData para consumidor final
  invoiceData.value.phone = telefonoConsumidor.value
  // Cargar formas de pago y mostrar modal
  await loadFormasPago()
  showFormaPagoModal.value = true
}

const cancelTelefonoConsumidor = () => {
  showTelefonoConsumidorModal.value = false
  showInvoiceModal.value = true
  telefonoConsumidor.value = ''
}

const confirmTelefonoPropio = async () => {
  if (!telefonoPropio.value || telefonoPropio.value.length !== 10 || !telefonoPropio.value.startsWith('3')) {
    await showAlert('warning', 'Teléfono inválido', 'El teléfono debe empezar por 3 y tener 10 dígitos')
    return
  }
  showTelefonoPropioModal.value = false
  // Actualizar teléfono en invoiceData
  invoiceData.value.phone = telefonoPropio.value
  
  // Si el tercero no tenía teléfono, actualizarlo en TNS
  if (wantsInvoice.value === 'propio' && invoiceData.value.document) {
    try {
      if (!session.selectedEmpresa.value) {
        await showAlert('error', 'Error', 'No hay empresa seleccionada')
        return
      }

      const empresaId = session.selectedEmpresa.value.empresaServidorId
      
      // Actualizar tercero en TNS con el teléfono
      await api.post('/api/tns/crear-tercero/', {
        empresa_servidor_id: empresaId,
        document_type: invoiceData.value.docType,
        document_number: invoiceData.value.document,
        nombre: invoiceData.value.name,
        email: invoiceData.value.email || '',
        telefono: telefonoPropio.value,
        nature: invoiceData.value.nature
      })
      
      console.log('✅ Teléfono actualizado en TNS')
    } catch (error: any) {
      console.error('Error actualizando teléfono en TNS:', error)
      // Continuar aunque falle
    }
  }
  
  // Cargar formas de pago y mostrar modal
  await loadFormasPago()
  showFormaPagoModal.value = true
}

const cancelTelefonoPropio = () => {
  showTelefonoPropioModal.value = false
  showCompleteDataModal.value = true
  telefonoPropio.value = ''
}

const loadFormasPago = async () => {
  if (!session.selectedEmpresa.value) {
    await showAlert('error', 'Error', 'No hay empresa seleccionada')
    return
  }

  if (!session.selectedEmpresa.value) {
    console.warn('[retail] No hay empresa seleccionada, no se pueden cargar formas de pago')
    return
  }
  
  loadingFormasPago.value = true
  try {
    const empresaId = session.selectedEmpresa.value.empresaServidorId
    const usuarioTns = session.tnsUsername.value || 'ADMIN'
    
    const response = await api.get('/api/cajas-autopago/formas-pago/', {
      empresa_servidor_id: empresaId,
      usuario_tns: usuarioTns
    })
    
    formasPago.value = response.formas_pago || []
    formaPagoSeleccionada.value = null
    
    console.log(`[retail] Formas de pago cargadas: ${formasPago.value.length} opciones`)
  } catch (error: any) {
    console.error('Error cargando formas de pago:', error)
    // No mostrar alerta aquí, solo loguear (se carga en background)
    formasPago.value = []
  } finally {
    loadingFormasPago.value = false
  }
}

const getPaymentIcon = (codigo: string): string => {
  const codigoUpper = codigo.toUpperCase()
  if (codigoUpper.includes('EFECTIVO') || codigoUpper.includes('CASH') || codigoUpper === 'EF') {
    return '💵'
  }
  if (codigoUpper.includes('TARJETA') || codigoUpper.includes('CARD') || codigoUpper.includes('TC')) {
    return '💳'
  }
  if (codigoUpper.includes('TRANSFERENCIA') || codigoUpper.includes('TRANS')) {
    return '🏦'
  }
  if (codigoUpper.includes('CHEQUE')) {
    return '📝'
  }
  return '💰'
}

const confirmFormaPago = () => {
  if (!formaPagoSeleccionada.value) {
    return
  }
  showFormaPagoModal.value = false
  // Proceder al pago real
  proceedToPaymentReal()
}

const cancelFormaPago = () => {
  showFormaPagoModal.value = false
  // Volver al modal anterior según el caso
  if (wantsInvoice.value === 'consumidor') {
    showTelefonoConsumidorModal.value = true
  } else {
    if (showTelefonoPropioModal.value) {
      showTelefonoPropioModal.value = true
    } else {
      showCompleteDataModal.value = true
    }
  }
  formaPagoSeleccionada.value = null
}

const proceedToPayment = async () => {
  // Validar formulario si es a nombre propio
  if (wantsInvoice.value === 'propio' && !isInvoiceFormValid.value) {
    return
  }
  
  // Validar teléfono según el caso
  if (wantsInvoice.value === 'consumidor') {
    // Consumidor final: siempre pedir teléfono
    if (!telefonoConsumidor.value || telefonoConsumidor.value.length < 7) {
      showTelefonoConsumidorModal.value = true
      return
    }
  } else if (wantsInvoice.value === 'propio') {
    // A nombre propio: pedir teléfono si no tiene
    if (!invoiceData.value.phone || invoiceData.value.phone.length < 7) {
      showTelefonoPropioModal.value = true
      return
    }
  } else if (orderType.value === 'takeaway') {
    // Para llevar sin factura: también pedir teléfono
    if (!telefonoConsumidor.value || telefonoConsumidor.value.length < 7) {
      showTelefonoConsumidorModal.value = true
      return
    }
  }
  
  // Si todo está bien, cargar formas de pago
  await loadFormasPago()
  if (formasPago.value.length > 0) {
    showFormaPagoModal.value = true
  } else {
    await showAlert('error', 'Error', 'No hay formas de pago disponibles')
  }
}

const proceedToPaymentReal = async () => {

  // Si es factura a nombre propio y tenemos todos los datos, crear/actualizar tercero en TNS
  if (wantsInvoice.value === 'propio' && invoiceData.value.document && invoiceData.value.name) {
    try {
      if (!session.selectedEmpresa.value) {
        await showAlert('error', 'Error', 'No hay empresa seleccionada')
        return
      }

      const empresaId = session.selectedEmpresa.value.empresaServidorId
      
      // Llamar al endpoint para crear/actualizar el tercero en TNS
      await api.post('/api/tns/crear-tercero/', {
        empresa_servidor_id: empresaId,
        document_type: invoiceData.value.docType, // 'cedula' o 'nit'
        document_number: invoiceData.value.document,
        nombre: invoiceData.value.name,
        email: invoiceData.value.email || '',
        telefono: invoiceData.value.phone || '',
        nature: invoiceData.value.nature // 'natural' o 'juridica'
      })
      
      console.log('✅ Tercero creado/actualizado en TNS correctamente')
    } catch (error: any) {
      console.error('Error creando/actualizando tercero en TNS:', error)
      const errorMsg = error?.data?.error || error?.message || 'Error al crear el tercero en TNS'
      await showAlert('warning', 'Advertencia', `No se pudo crear/actualizar el tercero en TNS: ${errorMsg}. Continuando con el pago...`)
      // Continuar con el pago aunque falle la creación del tercero
    }
  }

  // Recargar configuración de caja antes de procesar (por si se actualizó)
  await loadCajaConfig()

  // Si no hay caja configurada
  if (!currentCaja.value) {
    // Si es ADMIN, permitir pago de prueba con modo mock automático
    if (isAdmin.value) {
      const SwalInstance = (await import('sweetalert2')).default
      const result = await SwalInstance.fire({
        icon: 'question',
        title: 'Caja no configurada',
        text: 'No hay una caja autopago configurada. ¿Deseas hacer un pago de prueba en modo mock?',
        showCancelButton: true,
        confirmButtonText: 'Sí, pago de prueba',
        cancelButtonText: 'Configurar caja',
        confirmButtonColor: '#10B981',
        cancelButtonColor: '#DC2626',
        customClass: {
          container: 'swal-z-index-fix'
        }
      })
      
      if (result.isConfirmed) {
        // Usar caja temporal en modo mock para prueba
        currentCaja.value = {
          id: 'temp-mock',
          modo_mock: true,
          probabilidad_exito: 0.8,
          modo_mock_dian: true,
          activa: true
        }
      } else {
        showCajaConfigModal.value = true
        return
      }
    } else {
      // Si no es ADMIN, mostrar error y no permitir pago
      await showAlert('warning', 'Caja Autopago no configurada', 'Por favor, contacta al administrador para configurar la IP del datafono.')
      return
    }
  }

  // Cerrar modales
  showCompleteDataModal.value = false
  showInvoiceModal.value = false

  // Preparar datos del pedido
  const orderData = {
    orderType: orderType.value,
    cart: cart.value,
    total: cartTotal.value,
    invoice: wantsInvoice.value === 'propio' ? {
      docType: invoiceData.value.docType,
      nature: invoiceData.value.nature,
      document: invoiceData.value.document,
      name: invoiceData.value.name,
      email: invoiceData.value.email,
      phone: invoiceData.value.phone
    } : wantsInvoice.value === 'consumidor' ? {
      type: 'consumidor_final'
    } : null
  }

  console.log('Datos del pedido:', orderData)

  // Mostrar modal de pago en datafono
  showPaymentModal.value = true

  try {
    // Preparar datos del carrito completo
    const cartItems = cart.value
      .filter(item => !item.isSeparator) // Excluir separadores
      .map(item => ({
      id: item.id,
      name: item.name,
      price: item.price,
      quantity: item.quantity
    }))
    
    // Preparar datos de facturación (si aplica)
    const invoicePayload = wantsInvoice.value === 'propio' ? {
      docType: invoiceData.value.docType,
      document: invoiceData.value.document,
      name: invoiceData.value.name,
      email: invoiceData.value.email,
      phone: invoiceData.value.phone
    } : null
    
    // Construir observación
    let observacion = ''
    if (orderType.value === 'dinein' && mesaNumber.value) {
      observacion = `PARA COMER AQUÍ - MESA ${mesaNumber.value}`
    } else {
      observacion = 'PARA LLEVAR'
    }
    
    // Agregar teléfono a observación si existe
    const telefonoFinal = invoiceData.value.phone || telefonoConsumidor.value || ''
    if (telefonoFinal) {
      observacion += ` - TEL: ${telefonoFinal}`
    }
    
    // Agregar grupos de items separados por separadores (solo una vez)
    const gruposAgrupados = generarObservacionesAgrupadas()
    if (gruposAgrupados && gruposAgrupados.trim()) {
      observacion += ` ${gruposAgrupados}`
    }
    
    // Obtener usuario TNS
    const usuarioTns = session.tnsUsername.value || 'ADMIN'
    
    // Generar referencia única para el pedido
    const referencia = `PED-${Date.now()}`
    
    // Llamar al endpoint de procesar pago (solo procesa el pago, no crea factura)
    const response = await api.post(
      `/api/cajas-autopago/${currentCaja.value.id}/procesar-pago/`,
      {
        monto: cartTotal.value,
        referencia: referencia,
        descripcion: `Pedido ${orderType.value === 'takeaway' ? 'Para Llevar' : 'Para Comer Aquí'} - ${cart.value.length} items`
      }
    )

    // api.post devuelve directamente los datos, no response.data
    if (response.exito) {
      // Pago exitoso - Mostrar mensaje corto con auto-aceptar después de 2 segundos
      let mensajePago = `✅ Pago Aceptado\nNúmero: ${response.numero_aprobacion || 'N/A'}`
      if (response.modo_mock) {
        mensajePago += '\n(Modo Mock)'
      }
      
      // Cerrar modal de pago primero
      showPaymentModal.value = false
      
      // Si es exitoso, mostrar mensaje corto con auto-aceptar después de 2 segundos
      const SwalPago = (await import('sweetalert2')).default
      SwalPago.fire({
        icon: 'success',
        title: 'Pago Aprobado',
        text: mensajePago,
        timer: 2000,
        timerProgressBar: true,
        showConfirmButton: true,
        confirmButtonText: 'Aceptar',
        allowOutsideClick: false
      })
      
      // Esperar a que se cierre el modal de "Pago Aprobado" (2 segundos)
      await new Promise(resolve => setTimeout(resolve, 2100))
      
      // Mostrar "Realizando Pedido..." inmediatamente después
      const { default: Swal } = await import('sweetalert2')
      Swal.fire({
        icon: 'info',
        title: 'Realizando Pedido...',
        text: 'Procesando tu pedido, por favor espera...',
        showConfirmButton: false,
        allowOutsideClick: false,
        didOpen: () => {
          Swal.showLoading()
        }
      })
      
      // Pago exitoso - Ahora crear la factura en TNS
      console.log('✅ Pago aprobado, creando factura en TNS...')
      
      // Preparar datos del medio de pago del datafono
      const medioPagoData = {
        codigo_autorizacion: response.numero_aprobacion || '',
        franquicia: response.franquicia || '',
        ultimos_digitos: response.ultimos_digitos || '',
        tipo_cuenta: response.tipo_cuenta || '',
        numero_recibo: response.numero_recibo || '',
        rrn: response.rrn || ''
      }
      
      // Preparar datos de facturación
      const invoicePayload = wantsInvoice.value === 'propio' ? {
        docType: invoiceData.value.docType,
        document: invoiceData.value.document,
        name: invoiceData.value.name,
        email: invoiceData.value.email,
        phone: invoiceData.value.phone
      } : null
      
      // Reutilizar la observación que ya se construyó arriba (ya incluye grupos)
      // No duplicar los grupos, ya están en observacion
      const observacionFinal = observacion || ''
      
      // Obtener usuario TNS
      const usuarioTns = session.tnsUsername.value || 'ADMIN'
      
      // Llamar al endpoint para crear la factura en TNS
      // Swal ya está importado arriba, está disponible en este scope
      try {
        console.log('📋 Llamando a /api/dian-processor/crear-factura/...')
        const facturaResponse = await api.post('/api/dian-processor/crear-factura/', {
          empresa_servidor_id: session.selectedEmpresa.value?.empresaServidorId,
          empresa_nombre: companyName.value,
          empresa_nit: session.selectedEmpresa.value?.nit || '',
          cart_items: cartItems,
          monto_total: cartTotal.value,
          invoice_data: invoicePayload,
          order_type: orderType.value,
          referencia: referencia,
          forma_pago_codigo: formaPagoSeleccionada.value,
          mesa_number: mesaNumber.value || null,
          observacion: observacionFinal,
          usuario_tns: usuarioTns,
          medio_pago_data: medioPagoData
        })
        
        console.log('✅ Respuesta de crear-factura:', facturaResponse)
        
        // Cerrar el Swal de "Realizando Pedido..."
        Swal.close()
        
        if (facturaResponse.success && facturaResponse.kardex_id) {
          console.log('✅ Factura creada en TNS, KARDEXID:', facturaResponse.kardex_id)
          currentKardexId.value = facturaResponse.kardex_id
          currentEmpresaId.value = session.selectedEmpresa.value?.empresaServidorId || null
          
          // Guardar NIT normalizado para usar en DIAN
          const nitNormalizado = facturaResponse.nit_normalizado || '222222222222'
          
          // Mostrar "Pedido confirmado..."
          await showAlert('success', 'Pedido Confirmado', 'Tu pedido ha sido registrado exitosamente', 2000)
          
          // Mostrar "Enviando DIAN..." con loader
          Swal.fire({
            icon: 'info',
            title: 'Enviando DIAN...',
            text: 'Procesando factura electrónica, por favor espera...',
            showConfirmButton: false,
            allowOutsideClick: false,
            didOpen: () => {
              Swal.showLoading()
            }
          })
          
          // Inicializar estado del modal
          pdfCompletoDisponible.value = false
          pdfTabActiva.value = 'corto'
          
          // Generar PDF corto - cuando esté listo, abrir modal y cerrar Swal
          generarPdfTicketCorto().then(() => {
            // PDF corto listo - abrir modal y cerrar Swal
            if (ticketPdfUrl.value) {
              Swal.close()
              showInvoicePdfModal.value = true
              pdfTabActiva.value = 'corto'
              console.log('✅ PDF corto listo, modal abierto')
            }
          }).catch(err => {
            console.error('Error generando PDF corto:', err)
            // Cerrar Swal aunque falle
            Swal.close()
          })
          
          // Enviar a DIAN en paralelo - cuando responda, generar PDF grande
          api.post('/api/dian-processor/procesar-factura/', {
            nit: nitNormalizado,
            kardex_id: facturaResponse.kardex_id,
            empresa_servidor_id: currentEmpresaId.value,
            mock: currentCaja.value?.modo_mock_dian ?? true
          }).then((dianResponse) => {
            // DIAN respondió (exitosa o fallida) - generar PDF completo
            console.log(`✅ DIAN respondió: ${dianResponse?.status || 'sin respuesta'}, generando PDF completo...`)
            return generarPdfFacturaCompleta()
          }).then(() => {
            // PDF completo generado - actualizar estado
            pdfCompletoDisponible.value = true
            console.log('✅ PDF completo generado y disponible')
            
            // Si el usuario no ha cambiado de pestaña, cambiar a completo
            if (pdfTabActiva.value === 'corto') {
              pdfTabActiva.value = 'completo'
            }
          }).catch(err => {
            console.error('Error en proceso DIAN o generación PDF completo:', err)
            // Intentar generar PDF completo aunque DIAN haya fallado
            generarPdfFacturaCompleta().then(() => {
              pdfCompletoDisponible.value = true
            }).catch(e => {
              console.error('Error generando PDF completo como fallback:', e)
            })
          })
        } else {
          // Error al crear factura - Cerrar Swal de "Realizando Pedido..."
          const { default: SwalError } = await import('sweetalert2')
          SwalError.close()
          console.error('❌ Error al crear factura:', facturaResponse)
          await showAlert(
            'error',
            '⚠️ Error al Crear Factura',
            `El pago fue aprobado pero hubo un error al crear la factura: ${facturaResponse.error || 'Error desconocido'}`
          )
          
          // Limpiar y resetear
          cart.value = []
          showCart.value = false
          showPaymentModal.value = false
          showOrderTypeModal.value = true
          orderType.value = null
          mesaNumber.value = ''
          wantsInvoice.value = null
          invoiceData.value = {
            docType: 'cedula' as 'cedula' | 'nit',
            nature: 'natural' as 'natural' | 'juridica',
            document: '',
            name: '',
            email: '',
            phone: ''
          }
        }
      } catch (error: any) {
        // Cerrar Swal de "Realizando Pedido..." si hay error
        try {
          const { default: SwalError } = await import('sweetalert2')
          SwalError.close()
        } catch (e) {
          // Si no se puede cerrar, continuar
        }
        console.error('❌ Error al llamar crear-factura:', error)
        const errorMsg = error?.data?.error || error?.message || 'Error desconocido'
        await showAlert(
          'error',
          '⚠️ Error al Crear Factura',
          `El pago fue aprobado pero hubo un error al crear la factura: ${errorMsg}`
        )
        
        // Limpiar y resetear
        cart.value = []
        showCart.value = false
        showPaymentModal.value = false
        showOrderTypeModal.value = true
        orderType.value = null
        mesaNumber.value = ''
        wantsInvoice.value = null
        invoiceData.value = {
          docType: 'cedula' as 'cedula' | 'nit',
          nature: 'natural' as 'natural' | 'juridica',
          document: '',
          name: '',
          email: '',
          phone: ''
        }
      }
    } else {
      // Pago rechazado - Mostrar mensaje corto
      await showAlert(
        'error',
        '❌ Pago Rechazado',
        `${response.mensaje || 'El pago no pudo ser procesado'}${response.modo_mock ? '\n(Modo Mock)' : ''}`,
        3000
      )
      showPaymentModal.value = false
    }
  } catch (error: any) {
    console.error('Error procesando pago:', error)
    // $fetch puede devolver error.data o error directamente
    const errorMessage = error.data?.mensaje || error.mensaje || error.message || 'Error al procesar el pago'
    await showAlert('error', '❌ Error al Procesar Pago', errorMessage)
    showPaymentModal.value = false
  }
}

const cancelPayment = () => {
  showPaymentModal.value = false
  showCart.value = true
}

// Funciones para manejar PDF de factura después del pago
const showInvoicePdfOptions = async (nitNormalizado: string) => {
  if (!currentKardexId.value || !currentEmpresaId.value) {
    console.error('No hay kardex_id o empresa_id para mostrar PDF')
    return
  }
  
  try {
    // 1. Enviar a DIAN usando el endpoint procesar-factura
    // Obtener configuración de mock DIAN desde la caja actual
    const modoMockDian = currentCaja.value?.modo_mock_dian ?? true
    const mensajeMock = modoMockDian ? ' (mock)' : ''
    
    console.log(`📤 Enviando factura a DIAN${mensajeMock}...`)
    await showAlert('info', 'Enviando a DIAN', `Enviando factura a DIAN${mensajeMock}, por favor espere...`)
    
    const dianResponse = await api.post('/api/dian-processor/procesar-factura/', {
      nit: nitNormalizado,
      kardex_id: currentKardexId.value,
      empresa_servidor_id: currentEmpresaId.value,
      mock: modoMockDian  // Usar configuración de la caja
    })
    
    console.log('✅ Respuesta DIAN:', dianResponse)
    
    // 2. Sin importar si es exitoso o fallido, generar ambos PDFs (completo y corto) en paralelo
    console.log('📄 Generando PDFs...')
    isGeneratingPdf.value = true
    
    try {
      await Promise.all([
        generarPdfFacturaCompleta(),
        generarPdfTicketCorto()
      ])
      
      // 3. Mostrar modal con preview (mostrará PDF completo por defecto)
      showInvoicePdfModal.value = true
      console.log('✅ PDFs generados, mostrando modal')
    } finally {
      isGeneratingPdf.value = false
    }
    
  } catch (error: any) {
    console.error('❌ Error en flujo de PDF:', error)
    // Aún así, intentar generar PDFs aunque falle DIAN
    console.log('⚠️ Continuando con generación de PDFs aunque DIAN haya fallado...')
    isGeneratingPdf.value = true
    
    try {
      await Promise.all([
        generarPdfFacturaCompleta(),
        generarPdfTicketCorto()
      ])
      showInvoicePdfModal.value = true
    } finally {
      isGeneratingPdf.value = false
    }
  }
}

const generarPdfFacturaCompleta = async () => {
  if (!currentKardexId.value || !currentEmpresaId.value) {
    console.warn('Faltan datos para generar PDF completo')
    return
  }
  
  try {
    // Llamar al endpoint de Django (que tiene acceso directo a TNS)
    const config = useRuntimeConfig()
    const response = await $fetch('/api/dian-processor/generar-pdf-completo/', {
      baseURL: config.public.djangoApiUrl,
      method: 'POST',
      body: {
        kardex_id: currentKardexId.value,
        empresa_servidor_id: currentEmpresaId.value,
        empresa_nombre: companyName.value,
        empresa_nit: session.selectedEmpresa.value?.nit || ''
      },
      responseType: 'blob'
    })
    
    // Guardar blob y crear URL para preview
    pdfCompletoBlob.value = response as Blob
    invoicePdfUrl.value = URL.createObjectURL(response as Blob)
    console.log('✅ PDF completo generado desde Django')
  } catch (error: any) {
    console.error('Error generando PDF factura completa:', error)
    // No mostrar alerta aquí, solo loguear
  }
}

// Función única de impresión que imprime según la pestaña activa
const imprimirPdfActual = async () => {
  if (!currentKardexId.value || !currentEmpresaId.value || !currentCaja.value) {
    await showAlert('error', 'Error', 'Faltan datos para imprimir')
    return
  }
  
  try {
    if (pdfTabActiva.value === 'corto') {
      // Imprimir solo ticket corto en PRINTER_NAME
      if (!ticketCortoBlob.value) {
        await generarPdfTicketCorto()
        await new Promise(resolve => setTimeout(resolve, 1000))
      }
      
      if (!ticketCortoBlob.value) {
        await showAlert('error', 'Error', 'No se pudo generar el ticket para imprimir')
        return
      }
      
      const url = `http://${currentCaja.value.ip_datafono}:${currentCaja.value.puerto_datafono}/api/invoice/print-short`
      const formData = new FormData()
      formData.append('pdf', ticketCortoBlob.value, 'ticket_corto.pdf')
      formData.append('kardex_id', currentKardexId.value.toString())
      formData.append('empresa_servidor_id', currentEmpresaId.value.toString())
      formData.append('printer_type', 'main') // Imprimir en impresora principal
      
      const response = await $fetch(url, {
        method: 'POST',
        body: formData
      })
      
      if (response.success) {
        await showAlert('success', 'Impresión Enviada', 'El ticket se está imprimiendo')
        // Reiniciar ciclo: cerrar todo y volver a preguntar "para comer aquí" o "para llevar"
        resetearTodo()
        showInvoicePdfModal.value = false
        showOrderTypeModal.value = true
      } else {
        await showAlert('error', 'Error', response.message || 'No se pudo enviar a imprimir')
      }
    } else {
      // Imprimir factura completa en PRINTER_NAME y ticket corto en PRINTER_NAME_COMANDA
      // Asegurar que ambos PDFs estén generados
      if (!pdfCompletoBlob.value) {
        await generarPdfFacturaCompleta()
        await new Promise(resolve => setTimeout(resolve, 1000))
      }
      
      if (!ticketCortoBlob.value) {
        await generarPdfTicketCorto()
        await new Promise(resolve => setTimeout(resolve, 1000))
      }
      
      if (!pdfCompletoBlob.value) {
        await showAlert('error', 'Error', 'No se pudo generar el PDF para imprimir')
        return
      }
      
      if (!ticketCortoBlob.value) {
        await showAlert('warning', 'Advertencia', 'No se pudo generar el ticket corto para comanda')
        // Continuar solo con la factura completa
      }
      
      // Enviar ambos PDFs: factura completa + ticket corto para comanda
      const url = `http://${currentCaja.value.ip_datafono}:${currentCaja.value.puerto_datafono}/api/invoice/print-full`
      const formData = new FormData()
      formData.append('pdf', pdfCompletoBlob.value, 'factura_completa.pdf')
      if (ticketCortoBlob.value) {
        formData.append('pdf_comanda', ticketCortoBlob.value, 'ticket_corto.pdf')
      }
      formData.append('kardex_id', currentKardexId.value.toString())
      formData.append('empresa_servidor_id', currentEmpresaId.value.toString())
      
      const response = await $fetch(url, {
        method: 'POST',
        body: formData
      })
      
      if (response.success) {
        const message = response.comanda_impresa !== false 
          ? 'La factura completa y el ticket corto se están imprimiendo'
          : 'La factura completa se está imprimiendo (el ticket corto no se pudo imprimir en comanda)'
        await showAlert('success', 'Impresión Enviada', message)
        // Reiniciar ciclo: cerrar todo y volver a preguntar "para comer aquí" o "para llevar"
        resetearTodo()
        showInvoicePdfModal.value = false
        showOrderTypeModal.value = true
      } else {
        await showAlert('error', 'Error', response.message || 'No se pudo enviar a imprimir')
      }
    }
  } catch (error: any) {
    console.error('Error imprimiendo PDF:', error)
    await showAlert('error', 'Error', 'No se pudo enviar el PDF a imprimir')
  }
}

const imprimirFacturaCompleta = async () => {
  if (!currentKardexId.value || !currentEmpresaId.value || !currentCaja.value) {
    await showAlert('error', 'Error', 'Faltan datos para imprimir')
    return
  }
  
  try {
    // Si no hay PDF, generarlo primero
    if (!pdfCompletoBlob.value) {
      await generarPdfFacturaCompleta()
      await new Promise(resolve => setTimeout(resolve, 1000))
    }
    
    if (!pdfCompletoBlob.value) {
      await showAlert('error', 'Error', 'No se pudo generar el PDF para imprimir')
      return
    }
    
    // Enviar PDF al endpoint de impresión del datafono
    const url = `http://${currentCaja.value.ip_datafono}:${currentCaja.value.puerto_datafono}/api/invoice/print-full`
    
    // Convertir blob a FormData
    const formData = new FormData()
    formData.append('pdf', pdfCompletoBlob.value, 'factura_completa.pdf')
    formData.append('kardex_id', currentKardexId.value.toString())
    formData.append('empresa_servidor_id', currentEmpresaId.value.toString())
    
    const response = await $fetch(url, {
      method: 'POST',
      body: formData
    })
    
    if (response.success) {
      await showAlert('success', 'Impresión Enviada', 'La factura completa se está imprimiendo')
    } else {
      await showAlert('error', 'Error', response.message || 'No se pudo enviar a imprimir')
    }
  } catch (error: any) {
    console.error('Error imprimiendo factura completa:', error)
    await showAlert('error', 'Error', 'No se pudo enviar la factura a imprimir')
  }
}

const generarPdfTicketCorto = async () => {
  if (!currentKardexId.value || !currentEmpresaId.value) {
    console.warn('Faltan datos para generar ticket corto')
    return
  }
  
  isGeneratingPdf.value = true
  try {
    // Llamar al endpoint de Django (que tiene acceso directo a TNS)
    const config = useRuntimeConfig()
    const response = await $fetch('/api/dian-processor/generar-pdf-corto/', {
      baseURL: config.public.djangoApiUrl,
      method: 'POST',
      body: {
        kardex_id: currentKardexId.value,
        empresa_servidor_id: currentEmpresaId.value,
        empresa_nombre: companyName.value,
        empresa_nit: session.selectedEmpresa.value?.nit || ''
      },
      responseType: 'blob'
    })
    
    // Guardar blob y crear URL para preview
    ticketCortoBlob.value = response as Blob
    ticketPdfUrl.value = URL.createObjectURL(response as Blob)
    console.log('✅ Ticket corto generado desde Django')
  } catch (error: any) {
    console.error('Error generando ticket corto:', error)
    // No mostrar alerta aquí, solo loguear
  } finally {
    isGeneratingPdf.value = false
  }
}

const imprimirTicketCorto = async () => {
  if (!currentKardexId.value || !currentEmpresaId.value || !currentCaja.value) {
    await showAlert('error', 'Error', 'Faltan datos para imprimir')
    return
  }
  
  try {
    // Si no hay PDF, generarlo primero
    if (!ticketCortoBlob.value) {
      await generarPdfTicketCorto()
      await new Promise(resolve => setTimeout(resolve, 1000))
    }
    
    if (!ticketCortoBlob.value) {
      await showAlert('error', 'Error', 'No se pudo generar el ticket para imprimir')
      return
    }
    
    // Enviar PDF al endpoint de impresión del datafono
    const url = `http://${currentCaja.value.ip_datafono}:${currentCaja.value.puerto_datafono}/api/invoice/print-short`
    
    // Convertir blob a FormData
    const formData = new FormData()
    formData.append('pdf', ticketCortoBlob.value, 'ticket_corto.pdf')
    formData.append('kardex_id', currentKardexId.value.toString())
    formData.append('empresa_servidor_id', currentEmpresaId.value.toString())
    
    const response = await $fetch(url, {
      method: 'POST',
      body: formData
    })
    
    if (response.success) {
      await showAlert('success', 'Impresión Enviada', 'El ticket corto se está imprimiendo')
    } else {
      await showAlert('error', 'Error', response.message || 'No se pudo enviar a imprimir')
    }
  } catch (error: any) {
    console.error('Error imprimiendo ticket corto:', error)
    await showAlert('error', 'Error', 'No se pudo enviar el ticket a imprimir')
  }
}

const enviarSms = async () => {
  await showAlert('info', 'En Desarrollo', 'La funcionalidad de envío de SMS está en desarrollo')
}

const confirmarCerrarModalPdf = async () => {
  const result = await Swal.fire({
    title: '¿Salir sin imprimir?',
    text: '¿Estás seguro de que deseas salir sin imprimir ningún comprobante ni enviar SMS?',
    icon: 'warning',
    showCancelButton: true,
    confirmButtonText: 'Sí, salir',
    cancelButtonText: 'Cancelar',
    confirmButtonColor: '#DC2626',
    cancelButtonColor: '#6B7280'
  })
  
  if (result.isConfirmed) {
    cerrarModalPdf()
  }
}

// Función para cerrar el modal PDF sin imprimir (solo se puede cerrar después de confirmar)
const cerrarModalPdf = () => {
  showInvoicePdfModal.value = false
  showCart.value = false
  showOrderTypeModal.value = true
  orderType.value = null
}

// Funciones para edición de branding (solo ADMIN)
// loadBranding ya está definida arriba antes del watch

const openBrandingModal = async () => {
  if (!isAdmin.value) return
  showBrandingModal.value = true
  // Cargar branding actual antes de abrir el modal
  await loadBranding()
}

const saveBranding = async () => {
  if (!session.selectedEmpresa.value || !isAdmin.value) return
  uploadingImage.value = true
  try {
    const formData = new FormData()
    if (brandingData.value.logo) {
      formData.append('logo', brandingData.value.logo)
    }
    formData.append('color_primario', brandingData.value.color_primario)
    formData.append('color_secundario', brandingData.value.color_secundario)
    formData.append('color_fondo', brandingData.value.color_fondo)
    
    // Agregar videos si existen
    if (brandingData.value.video_por_defecto) {
      formData.append('video_por_defecto', brandingData.value.video_por_defecto)
    }
    if (brandingData.value.video_lunes) {
      formData.append('video_lunes', brandingData.value.video_lunes)
    }
    if (brandingData.value.video_martes) {
      formData.append('video_martes', brandingData.value.video_martes)
    }
    if (brandingData.value.video_miercoles) {
      formData.append('video_miercoles', brandingData.value.video_miercoles)
    }
    if (brandingData.value.video_jueves) {
      formData.append('video_jueves', brandingData.value.video_jueves)
    }
    if (brandingData.value.video_viernes) {
      formData.append('video_viernes', brandingData.value.video_viernes)
    }
    if (brandingData.value.video_sabado) {
      formData.append('video_sabado', brandingData.value.video_sabado)
    }
    if (brandingData.value.video_domingo) {
      formData.append('video_domingo', brandingData.value.video_domingo)
    }
    
    formData.append('empresa_servidor_id', String(session.selectedEmpresa.value.empresaServidorId))
    formData.append('nit', session.selectedEmpresa.value.nit || '')
    formData.append('tns_username', session.tnsUsername.value || '')
    formData.append('modo_visualizacion', currentBranding.value.modo_visualizacion || 'vertical')
    
    // No establecer Content-Type manualmente - el navegador lo hace automáticamente con FormData
    await api.patch('/api/branding/empresa/', formData)
    
    // Recargar branding después de guardar
    await loadBranding()
    showBrandingModal.value = false
    // Recargar productos para aplicar nuevos colores
    await loadProducts(isAdmin.value)
  } catch (error) {
    console.error('Error guardando branding:', error)
    await showAlert('error', 'Error al guardar branding', 'No se pudo guardar la configuración. Intenta nuevamente.')
  } finally {
    uploadingImage.value = false
  }
}

// Funciones para gestionar caja autopago
const loadCajaConfig = async () => {
  if (!session.selectedEmpresa.value) return
  
  try {
    const empresaId = session.selectedEmpresa.value.empresaServidorId
    const response = await api.get('/api/cajas-autopago/por-empresa/', {
      empresa_servidor_id: empresaId
    }).then((r: any) => r.data || r)
    
    console.log('[retail] Cajas cargadas:', response)
    
    // Si hay cajas, tomar la primera activa o la primera disponible
    if (response && Array.isArray(response) && response.length > 0) {
      const cajaActiva = response.find((c: any) => c.activa) || response[0]
      currentCaja.value = cajaActiva
      
      console.log('[retail] Caja seleccionada:', currentCaja.value)
      
      // Cargar configuración en el formulario
      cajaConfig.value = {
        nombre: cajaActiva.nombre || '',
        ip_datafono: cajaActiva.ip_datafono || '',
        puerto_datafono: cajaActiva.puerto_datafono || 8080,
        modo_mock: cajaActiva.modo_mock || false,
        probabilidad_exito: cajaActiva.probabilidad_exito || 0.8,
        modo_mock_dian: cajaActiva.modo_mock_dian !== undefined ? cajaActiva.modo_mock_dian : true,
        activa: cajaActiva.activa !== false
      }
    } else {
      // No hay caja configurada, inicializar con valores por defecto
      console.log('[retail] No se encontraron cajas para la empresa')
      currentCaja.value = null
      cajaConfig.value = {
        nombre: 'Caja Principal',
        ip_datafono: '',
        puerto_datafono: 8080,
        modo_mock: true,
        probabilidad_exito: 0.8,
        modo_mock_dian: true,
        activa: true
      }
    }
  } catch (error) {
    console.error('Error cargando configuración de caja:', error)
    currentCaja.value = null
  }
}

const openCajaConfigModal = async () => {
  if (!isAdmin.value) return
  await loadCajaConfig()
  showCajaConfigModal.value = true
}

// Funciones para cambio de usuario
const cancelUserSwitch = () => {
  // Cancelar: cerrar modal y limpiar formulario sin hacer cambios
  showUserSwitchModal.value = false
  userSwitchForm.password = ''
  userSwitchError.value = null
  switchingUser.value = false
  console.log('[retail] Cambio de usuario cancelado, manteniendo usuario actual')
}

const switchToCajagc = async () => {
  // Volver a CAJAGC: limpiar validación TNS pero mantener empresa
  switchingUser.value = true
  userSwitchError.value = null
  
  try {
    // Limpiar validación TNS (esto hace que isAdmin sea false)
    // Pasar un objeto sin username para que setTNSValidation limpie tnsUsername
    session.setTNSValidation({ VALIDATE: { OUSERNAME: '' }, MODULOS: {} })
    
    // Limpiar sessionStorage de validaciones TNS
    if (typeof window !== 'undefined') {
      const empresaId = session.selectedEmpresa.value?.empresaServidorId
      if (empresaId) {
        const prefix = `tns_validation_${empresaId}_`
        const keysToRemove: string[] = []
        for (let i = 0; i < sessionStorage.length; i++) {
          const key = sessionStorage.key(i)
          if (key && key.startsWith(prefix)) {
            keysToRemove.push(key)
          }
        }
        keysToRemove.forEach((k) => sessionStorage.removeItem(k))
        console.log('[retail] Validaciones TNS limpiadas de sessionStorage')
      }
    }
    
    // Recargar productos sin forzar (usará caché si está disponible)
    await loadProducts(false)
    
    showUserSwitchModal.value = false
    console.log('[retail] ✅ Cambiado a modo CAJAGC')
  } catch (error: any) {
    console.error('[retail] Error cambiando a CAJAGC:', error)
    userSwitchError.value = 'Error al cambiar a CAJAGC'
  } finally {
    switchingUser.value = false
  }
}

const handleUserSwitchLogin = async () => {
  // Cambiar a Admin: validar usuario TNS
  switchingUser.value = true
  userSwitchError.value = null
  
  try {
    const empresaId = session.selectedEmpresa.value?.empresaServidorId
    if (!empresaId) {
      throw new Error('No hay empresa seleccionada')
    }
    
    // Validar usuario TNS usando la función del session store
    // Usuario fijo: ADMIN
    await session.validateTNSUser({
      empresa_servidor_id: empresaId,
      username: 'ADMIN',
      password: userSwitchForm.password
    })
    
    // Si la validación es exitosa, el usuario ahora es admin
    // Recargar productos forzando actualización (admin siempre fuerza)
    await loadProducts(true)
    
    // Limpiar formulario y cerrar modal
    userSwitchForm.password = ''
    showUserSwitchModal.value = false
    
    console.log('[retail] ✅ Cambiado a modo Admin')
  } catch (error: any) {
    // Si falla, mantener el usuario actual (CAJAGC)
    console.error('[retail] Error en login de admin:', error)
    userSwitchError.value = error?.data?.message || error?.data?.detail || 'Usuario o contraseña incorrectos'
    // NO limpiar el formulario para que el usuario pueda intentar de nuevo
  } finally {
    switchingUser.value = false
  }
}

const saveCajaConfig = async () => {
  if (!session.selectedEmpresa.value || !isAdmin.value) return
  
  try {
    const empresaId = session.selectedEmpresa.value.empresaServidorId
    const tnsUsername = session.tnsUsername.value || ''
    
    const payload: any = {
      empresa_servidor: empresaId,
      nombre: cajaConfig.value.nombre,
      ip_datafono: cajaConfig.value.ip_datafono,
      puerto_datafono: cajaConfig.value.puerto_datafono,
      modo_mock: cajaConfig.value.modo_mock,
      probabilidad_exito: cajaConfig.value.probabilidad_exito,
      modo_mock_dian: cajaConfig.value.modo_mock_dian,
      activa: cajaConfig.value.activa,
      usuario_tns: tnsUsername
    }
    
    if (currentCaja.value?.id) {
      // Actualizar caja existente
      await api.patch(`/api/cajas-autopago/${currentCaja.value.id}/`, payload)
    } else {
      // Crear nueva caja
      await api.post('/api/cajas-autopago/', payload)
    }
    
    // Recargar configuración (esperar un poco para que el backend procese)
    await new Promise(resolve => setTimeout(resolve, 500))
    await loadCajaConfig()
    
    // Verificar que se cargó correctamente
    if (currentCaja.value && currentCaja.value.ip_datafono) {
      showCajaConfigModal.value = false
      await showAlert('success', '✅ Configuración Guardada', `La configuración de la caja "${currentCaja.value.nombre}" se guardó correctamente.\nIP: ${currentCaja.value.ip_datafono}:${currentCaja.value.puerto_datafono}`)
    } else {
      // Si no se cargó, intentar de nuevo
      await new Promise(resolve => setTimeout(resolve, 500))
      await loadCajaConfig()
      showCajaConfigModal.value = false
      if (currentCaja.value && currentCaja.value.ip_datafono) {
        await showAlert('success', '✅ Configuración Guardada', 'La configuración se guardó correctamente.')
      } else {
        await showAlert('warning', '⚠️ Configuración Guardada', 'La configuración se guardó, pero no se pudo verificar. Recarga la página si es necesario.')
      }
    }
  } catch (error: any) {
    console.error('Error guardando configuración de caja:', error)
    await showAlert('error', 'Error al Guardar', error.response?.data?.error || error.message || 'Error desconocido')
  }
}

const openGrupoImageEditor = async (gmCodigo: string) => {
  if (!isAdmin.value) return
  editingGrupo.value = gmCodigo
  // Buscar la descripción de la categoría en allGroups o categories
  let categoria = allGroups.value.find((g: any) => (g.gm_codigo || g.codigo) === gmCodigo)
  if (!categoria) {
    categoria = categories.value.find((c: any) => (c.gm_codigo || c.id) === gmCodigo)
  }
  editingGrupoDescrip.value = categoria?.gm_descrip || categoria?.descrip || categoria?.name || null
  notaEnEdicion.value = null // Resetear nota en edición
  showGrupoImageModal.value = true
  // Cargar notas rápidas de esta categoría
  await cargarNotasRapidasCategoria(gmCodigo)
}

const cargarNotasRapidasCategoria = async (gmCodigo: string) => {
  try {
    const response = await api.get('/api/notas-rapidas/list/', {
      empresa_servidor_id: session.selectedEmpresa.value?.empresaServidorId,
      categoria: gmCodigo,
      activo: true
    })
    console.log('[retail] Respuesta de notas rápidas de categoría:', response)
    // El backend retorna { success: true, data: [...] }
    if (response && response.success && response.data) {
      notasRapidasCategoria.value = response.data || []
    } else if (Array.isArray(response)) {
      // Si la respuesta es directamente un array
      notasRapidasCategoria.value = response
    } else if (response && response.data) {
      // Si la respuesta tiene data directamente
      notasRapidasCategoria.value = Array.isArray(response.data) ? response.data : []
    } else {
      notasRapidasCategoria.value = []
    }
    console.log('[retail] Notas rápidas cargadas:', notasRapidasCategoria.value)
  } catch (error) {
    console.error('Error cargando notas rápidas de categoría:', error)
    notasRapidasCategoria.value = []
  }
}

const guardarNotaRapida = async () => {
  if (!nuevaNotaRapidaTexto.value || !nuevaNotaRapidaTexto.value.trim() || !editingGrupo.value) return
  
  try {
    if (editandoNotaRapida.value) {
      // Actualizar nota existente
      await api.put(`/api/notas-rapidas/${editandoNotaRapida.value.id}/actualizar/`, {
        texto: nuevaNotaRapidaTexto.value.trim(),
        categorias: [editingGrupo.value],
        activo: true
      })
    } else {
      // Crear nueva nota
      await api.post('/api/notas-rapidas/crear/', {
        texto: nuevaNotaRapidaTexto.value.trim(),
        categorias: [editingGrupo.value],
        orden: notasRapidasCategoria.value.length,
        activo: true
      })
    }
    
    // Recargar notas de la categoría
    await cargarNotasRapidasCategoria(editingGrupo.value)
    // Recargar todas las notas rápidas para que se actualicen en el modal de notas
    await loadNotasRapidas()
    
    // Limpiar formulario
    nuevaNotaRapidaTexto.value = ''
    editandoNotaRapida.value = null
    
    await showAlert('success', 'Éxito', editandoNotaRapida.value ? 'Nota rápida actualizada' : 'Nota rápida creada')
  } catch (error: any) {
    console.error('Error guardando nota rápida:', error)
    await showAlert('error', 'Error', error.response?.data?.error || 'No se pudo guardar la nota rápida')
  }
}

const editarNotaRapida = (nota: {id: number, texto: string}) => {
  editandoNotaRapida.value = { id: nota.id, texto: nota.texto }
  nuevaNotaRapidaTexto.value = nota.texto
  notaEnEdicion.value = null // Cerrar el menú de opciones
}

const cancelarEdicionNotaRapida = () => {
  editandoNotaRapida.value = null
  nuevaNotaRapidaTexto.value = ''
  notaEnEdicion.value = null // Cerrar el menú de opciones
}

const eliminarNotaRapida = async (id: number) => {
  notaEnEdicion.value = null // Cerrar el menú de opciones
  if (!confirm('¿Estás seguro de que quieres eliminar esta opción rápida?')) return
  
  try {
    await api.delete(`/api/notas-rapidas/${id}/eliminar/`)
    // Recargar notas de la categoría
    if (editingGrupo.value) {
      await cargarNotasRapidasCategoria(editingGrupo.value)
    }
    // Recargar todas las notas rápidas
    await loadNotasRapidas()
    await showAlert('success', 'Éxito', 'Nota rápida eliminada')
  } catch (error: any) {
    console.error('Error eliminando nota rápida:', error)
    await showAlert('error', 'Error', error.response?.data?.error || 'No se pudo eliminar la nota rápida')
  }
}

const saveGrupoImage = async (file: File) => {
  if (!session.selectedEmpresa.value || !editingGrupo.value || !isAdmin.value) return
  uploadingImage.value = true
  try {
    const formData = new FormData()
    formData.append('imagen', file)
    formData.append('gm_codigo', editingGrupo.value)
    formData.append('empresa_servidor_id', String(session.selectedEmpresa.value.empresaServidorId))
    formData.append('nit', session.selectedEmpresa.value.nit || '')
    formData.append('tns_username', session.tnsUsername.value || '')
    
    console.log('[retail] Guardando imagen de grupo:', { gm_codigo: editingGrupo.value, file: file.name })
    
    // No establecer Content-Type manualmente - el navegador lo hace automáticamente con FormData
    await api.patch('/api/branding/grupo/', formData)
    // Recargar productos para mostrar la nueva imagen
    await loadProducts(isAdmin.value)
    showGrupoImageModal.value = false
    editingGrupo.value = null
  } catch (error) {
    console.error('Error guardando imagen de grupo:', error)
    await showAlert('error', 'Error al guardar imagen', 'No se pudo guardar la imagen de la categoría. Intenta nuevamente.')
  } finally {
    uploadingImage.value = false
  }
}

const openProductView = async (product: any) => {
  viewingProduct.value = product
  showProductViewModal.value = true
  
  // Cargar datos del material (imagen, características) si existe
  if (product.codigo && session.selectedEmpresa.value) {
    try {
      const nit = session.selectedEmpresa.value.nit
      const empresaId = session.selectedEmpresa.value.empresaServidorId
      const response = await api.get('/api/branding/material/', {
        empresa_servidor_id: empresaId, 
        nit: nit, 
        codigo_material: product.codigo,
        tns_username: session.tnsUsername.value || ''
      })
      productMaterialData.value = response
    } catch (error) {
      console.error('Error cargando datos del material:', error)
      productMaterialData.value = null
    }
  } else {
    productMaterialData.value = null
  }
}

const openMaterialImageEditor = async (codigo: string) => {
  if (!isAdmin.value) return
  editingMaterial.value = codigo
  showMaterialImageModal.value = true
  
  // Cargar datos actuales del material
  if (codigo && session.selectedEmpresa.value) {
    try {
      const nit = session.selectedEmpresa.value.nit
      const empresaId = session.selectedEmpresa.value.empresaServidorId
      const response = await api.get('/api/branding/material/', {
        empresa_servidor_id: empresaId, 
        nit: nit, 
        codigo_material: codigo,
        tns_username: session.tnsUsername.value || ''
      })
      currentMaterialImage.value = response.imagen_url
      materialEditData.value = {
        caracteristicas: response.caracteristicas || ''
      }
    } catch (error) {
      console.error('Error cargando datos del material:', error)
      currentMaterialImage.value = null
      materialEditData.value = { caracteristicas: '' }
    }
  }
}

const saveMaterialImage = async (file?: File) => {
  if (!session.selectedEmpresa.value || !editingMaterial.value || !isAdmin.value) return
  uploadingImage.value = true
  try {
    const formData = new FormData()
    if (file) {
      formData.append('imagen', file)
    }
    formData.append('codigo_material', editingMaterial.value)
    formData.append('empresa_servidor_id', String(session.selectedEmpresa.value.empresaServidorId))
    formData.append('nit', session.selectedEmpresa.value.nit || '')
    formData.append('tns_username', session.tnsUsername.value || '')
    
    // Agregar características si están presentes
    if (materialEditData.value.caracteristicas !== undefined) {
      formData.append('caracteristicas', materialEditData.value.caracteristicas || '')
    }
    
    console.log('[retail] Guardando material:', { 
      codigo_material: editingMaterial.value, 
      file: file?.name,
      caracteristicas: materialEditData.value.caracteristicas 
    })
    
    // No establecer Content-Type manualmente - el navegador lo hace automáticamente con FormData
    await api.patch('/api/branding/material/', formData)
    // Recargar productos para mostrar la nueva imagen
    await loadProducts(isAdmin.value)
    showMaterialImageModal.value = false
    editingMaterial.value = null
    materialEditData.value = { caracteristicas: '' }
  } catch (error) {
    console.error('Error guardando material:', error)
    await showAlert('error', 'Error al guardar material', 'No se pudo guardar la imagen o características del producto. Intenta nuevamente.')
  } finally {
    uploadingImage.value = false
  }
}

// Validación del formulario de factura
const isInvoiceFormValid = computed(() => {
  if (wantsInvoice.value !== 'propio') return true
  
  return !!(
    invoiceData.value.docType &&
    invoiceData.value.nature &&
    invoiceData.value.document &&
    invoiceData.value.document.length >= 7 &&
    invoiceData.value.name &&
    invoiceData.value.name.length >= 3 &&
    invoiceData.value.email &&
    invoiceData.value.email.includes('@') &&
    invoiceData.value.phone &&
    invoiceData.value.phone.length === 10 &&
    invoiceData.value.phone.startsWith('3')
  )
})

// Funciones para manejo de teclado virtual
const onKeyboardModeChange = async () => {
  if (!isAdmin.value || !session.selectedEmpresa.value) return
  
  try {
    const empresaId = session.selectedEmpresa.value.empresaServidorId
    const nit = session.selectedEmpresa.value.nit
    const tnsUsername = session.tnsUsername.value || ''
    
    // Guardar modo_teclado en el backend
    const formData = new FormData()
    formData.append('modo_teclado', keyboardMode.value)
    formData.append('empresa_servidor_id', String(empresaId))
    formData.append('nit', nit)
    formData.append('tns_username', tnsUsername)
    
    // Mantener los valores existentes de branding
    if (currentBranding.value.color_primario) {
      formData.append('color_primario', currentBranding.value.color_primario)
    }
    if (currentBranding.value.color_secundario) {
      formData.append('color_secundario', currentBranding.value.color_secundario)
    }
    if (currentBranding.value.color_fondo) {
      formData.append('color_fondo', currentBranding.value.color_fondo)
    }
    
    await api.patch('/api/branding/empresa/', formData)
    
    // Actualizar currentBranding
    currentBranding.value.modo_teclado = keyboardMode.value
    
    console.log('[retail] Modo de teclado guardado:', keyboardMode.value)
  } catch (error) {
    console.error('Error guardando modo de teclado:', error)
    await showAlert('error', 'Error al guardar modo de teclado', 'No se pudo guardar la configuración del teclado. Intenta nuevamente.')
  }
}

const shouldUseVirtualKeyboard = (inputType: 'numeric' | 'text' | 'email'): boolean => {
  if (!process.client) return false
  if (keyboardMode.value === 'auto') return false
  if (keyboardMode.value === 'virtual') return true
  if (keyboardMode.value === 'hybrid') {
    // En híbrido, usar virtual solo en desktop (pantallas grandes)
    return window.innerWidth > 768
  }
  return false
}

const openVirtualKeyboard = (element: HTMLInputElement | null, type: 'numeric' | 'text' | 'email') => {
  if (!element || !process.client) return
  if (!shouldUseVirtualKeyboard(type)) return
  
  // Verificar que el elemento esté en el DOM
  if (!element.parentNode) {
    console.warn('Elemento no está en el DOM aún')
    return
  }
  
  activeInput.value = { element, type }
  showVirtualKeyboard.value = true
  element.readOnly = true
  isShiftActive.value = false // Resetear shift al abrir teclado
  
  // Usar nextTick para asegurar que el DOM esté actualizado
  nextTick(() => {
    if (element && element.parentNode) {
      element.focus()
    }
  })
}

const closeVirtualKeyboard = () => {
  if (activeInput.value.element) {
    activeInput.value.element.readOnly = false
  }
  showVirtualKeyboard.value = false
  activeInput.value = { element: null, type: 'text' }
}

// Helper para manejar click en input de notas rápidas
const handleNotaRapidaInputClick = (e: Event) => {
  const target = e.target as HTMLInputElement
  if (target && shouldUseVirtualKeyboard('text')) {
    target.focus()
    if (typeof window !== 'undefined' && window.setTimeout) {
      window.setTimeout(() => openVirtualKeyboard(target, 'text'), 100)
    }
  }
}

const toggleShift = () => {
  isShiftActive.value = !isShiftActive.value
}

const virtualKeyPress = (key: string) => {
  if (!activeInput.value.element) return
  
  const input = activeInput.value.element
  const currentValue = input.value
  const cursorPos = input.selectionStart || currentValue.length
  
  if (key === 'backspace') {
    input.value = currentValue.slice(0, cursorPos - 1) + currentValue.slice(cursorPos)
    input.dispatchEvent(new Event('input', { bubbles: true }))
    input.setSelectionRange(cursorPos - 1, cursorPos - 1)
  } else if (key === 'space') {
    input.value = currentValue.slice(0, cursorPos) + ' ' + currentValue.slice(cursorPos)
    input.dispatchEvent(new Event('input', { bubbles: true }))
    input.setSelectionRange(cursorPos + 1, cursorPos + 1)
  } else {
    input.value = currentValue.slice(0, cursorPos) + key + currentValue.slice(cursorPos)
    input.dispatchEvent(new Event('input', { bubbles: true }))
    input.setSelectionRange(cursorPos + 1, cursorPos + 1)
    // Desactivar shift después de presionar una letra (comportamiento común)
    if (isShiftActive.value && /[a-zA-Z]/.test(key)) {
      isShiftActive.value = false
    }
  }
}

// El modo de teclado ahora se carga desde el backend en loadBranding()

// ========== FUNCIONES DEL PROTECTOR DE PANTALLA ==========

// Cachear video: descargar y convertir a blob URL para cacheo
const cacheVideo = async (videoUrl: string): Promise<string> => {
  if (!process.client) return videoUrl
  
  // Si ya está en cache, retornar
  if (videoCache.value.has(videoUrl)) {
    return videoCache.value.get(videoUrl)!
  }
  
  try {
    // Descargar video
    const response = await fetch(videoUrl)
    const blob = await response.blob()
    const blobUrl = URL.createObjectURL(blob)
    
    // Guardar en cache
    videoCache.value.set(videoUrl, blobUrl)
    
    console.log('[screensaver] Video cacheado:', videoUrl)
    return blobUrl
  } catch (error) {
    console.error('[screensaver] Error cacheando video:', error)
    return videoUrl // Fallback a URL original
  }
}

// Preparar secuencia de videos
const prepareVideoSequence = async () => {
  if (!currentBranding.value) return
  
  const sequence: string[] = []
  
  // 1. Video por defecto (si existe)
  if (currentBranding.value.video_por_defecto_url) {
    const cachedUrl = await cacheVideo(currentBranding.value.video_por_defecto_url)
    sequence.push(cachedUrl)
  }
  
  // 2. Video del día (si existe)
  if (currentBranding.value.video_del_dia_url) {
    const cachedUrl = await cacheVideo(currentBranding.value.video_del_dia_url)
    sequence.push(cachedUrl)
  }
  
  videoSequence.value = sequence
  currentVideoIndex.value = 0
  
  console.log('[screensaver] Secuencia de videos preparada:', sequence.length, 'videos')
}

// Reproducir siguiente video en la secuencia
const playNextVideo = () => {
  if (videoSequence.value.length === 0) {
    hideScreensaver()
    return
  }
  
  const videoUrl = videoSequence.value[currentVideoIndex.value]
  currentVideoUrl.value = videoUrl
  
  // Avanzar al siguiente video (circular)
  currentVideoIndex.value = (currentVideoIndex.value + 1) % videoSequence.value.length
  
  // Cuando el video termine, reproducir el siguiente
  if (screensaverVideo.value) {
    screensaverVideo.value.onended = () => {
      if (videoSequence.value.length > 1) {
        playNextVideo()
      } else {
        // Si solo hay un video, hacer loop
        screensaverVideo.value?.play()
      }
    }
  }
}

// Detectar formato del video y ajustar
const onVideoLoaded = () => {
  if (!screensaverVideo.value) return
  
  const video = screensaverVideo.value
  const container = video.parentElement
  const videoAspectRatio = video.videoWidth / video.videoHeight
  const screenAspectRatio = window.innerWidth / window.innerHeight
  
  // Si el video es vertical (aspect ratio < 1) y la pantalla es horizontal
  // o viceversa, ajustar con object-fit
  if (videoAspectRatio < 1 && screenAspectRatio > 1) {
    // Video vertical en pantalla horizontal: usar contain con blur de fondo
    video.style.objectFit = 'contain'
    container?.classList.add('video-contain')
  } else if (videoAspectRatio > 1 && screenAspectRatio < 1) {
    // Video horizontal en pantalla vertical: usar contain con blur de fondo
    video.style.objectFit = 'contain'
    container?.classList.add('video-contain')
  } else {
    // Mismo formato: usar cover para llenar
    video.style.objectFit = 'cover'
    container?.classList.remove('video-contain')
  }
  
  video.play().catch(err => {
    console.error('[screensaver] Error reproduciendo video:', err)
  })
}

// Mostrar protector de pantalla
const showScreensaverFunc = async () => {
  if (showScreensaver.value) return // Ya está mostrando
  
  await prepareVideoSequence()
  
  if (videoSequence.value.length === 0) {
    console.log('[screensaver] No hay videos configurados')
    return
  }
  
  showScreensaver.value = true
  playNextVideo()
  
  console.log('[screensaver] Protector de pantalla activado')
}

// Ocultar protector de pantalla
const hideScreensaver = () => {
  if (screensaverVideo.value) {
    screensaverVideo.value.pause()
    screensaverVideo.value.currentTime = 0
  }
  showScreensaver.value = false
  resetInactivityTimer()
  console.log('[screensaver] Protector de pantalla desactivado')
}

// Resetear timer de inactividad
const resetInactivityTimer = () => {
  if (inactivityTimer.value) {
    clearTimeout(inactivityTimer.value)
  }
  
  if (!process.client) return
  
  inactivityTimer.value = setTimeout(() => {
    showScreensaverFunc()
  }, INACTIVITY_TIMEOUT)
}

// Detectar actividad del usuario
const setupInactivityDetection = () => {
  if (!process.client) return
  
  const events = ['mousedown', 'mousemove', 'keypress', 'scroll', 'touchstart', 'click']
  
  events.forEach(event => {
    document.addEventListener(event, resetInactivityTimer, { passive: true })
  })
  
  // Iniciar timer
  resetInactivityTimer()
  
  console.log('[screensaver] Detección de inactividad configurada')
}

// Limpiar cache de videos al desmontar
onUnmounted(() => {
  if (inactivityTimer.value) {
    clearTimeout(inactivityTimer.value)
  }
  
  // Limpiar blob URLs del cache
  videoCache.value.forEach(blobUrl => {
    URL.revokeObjectURL(blobUrl)
  })
  videoCache.value.clear()
})

// Configurar detección de inactividad cuando se carga el branding
watch(() => currentBranding.value.video_por_defecto_url, () => {
  if (process.client && currentBranding.value.video_por_defecto_url) {
    setupInactivityDetection()
  }
}, { immediate: true })
</script>

<style scoped>
/* Debug Banner */
.debug-banner {
  position: fixed;
  top: 0;
  left: 0;
  right: 0;
  color: white;
  padding: 0.75rem;
  text-align: center;
  z-index: 10000;
  font-weight: bold;
  box-shadow: 0 2px 10px rgba(0,0,0,0.3);
}

.debug-banner.admin-mode {
  /* Color se aplica dinámicamente desde :style */
}

.debug-banner.user-mode {
  background: #666;
}

.autopago-container {
  min-height: 100vh;
  background: var(--color-fondo, #f5f5f5); /* Fondo dinámico desde branding */
  padding: 1rem;
  padding-top: 1.5rem; /* Reducido, ya no usamos banner superior fijo */
  max-width: 1400px;
  margin: 0 auto;
  width: 100%;
  box-sizing: border-box;
  overflow-x: hidden; /* Evitar desbordamiento horizontal */
}

/* Selector de modo de teclado (Debug) */
.keyboard-mode-selector {
  position: fixed;
  top: 10px;
  right: 10px;
  background: rgba(255, 255, 255, 0.95);
  padding: 0.75rem 1rem;
  border-radius: 8px;
  box-shadow: 0 4px 12px rgba(0, 0, 0, 0.15);
  z-index: 10000;
  font-size: 0.85rem;
}

.keyboard-mode-selector label {
  display: flex;
  align-items: center;
  gap: 0.5rem;
  font-weight: 600;
  color: #333;
}

.keyboard-mode-selector select {
  padding: 0.5rem;
  border: 2px solid #ddd;
  border-radius: 6px;
  font-size: 0.85rem;
  background: white;
  cursor: pointer;
}

.keyboard-mode-selector select:focus {
  outline: none;
  border-color: var(--color-primario, #DC2626);
}

/* Header */
.autopago-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  gap: 1rem;
  background: white;
  padding: 1rem 1.5rem;
  border-radius: 20px;
  margin: 0 auto 1.5rem auto;
  max-width: 1400px;
  width: 100%;
  box-sizing: border-box;
  box-shadow: 0 4px 20px rgba(0, 0, 0, 0.1);
  position: sticky;
  top: 0;
  z-index: 100;
}

.autopago-header.modo-horizontal-header {
  display: grid;
  grid-template-columns: auto 1fr; /* Logo | (Nombre + buscador + categorías) */
  gap: 0.5rem;
  align-items: flex-start;
  padding: 0.75rem 1rem;
  margin: 0 auto 0.75rem auto;
}

.autopago-header.modo-horizontal-header .logo-section {
  grid-column: 1;
}

.autopago-header.modo-horizontal-header .categories-in-header-wrapper {
  grid-column: 2;
  align-self: stretch;
  display: flex;
  flex-direction: column;
  justify-content: flex-start;
  min-width: 0;
  max-width: 100%;
  margin-left: 0.25rem;
}

/* Controles admin en modo horizontal (dentro de categorías) */
.header-controls-horizontal-admin {
  display: flex;
  gap: 0.5rem;
  margin-bottom: 0.25rem;
  justify-content: flex-end;
  flex-wrap: wrap;
}

.autopago-header.modo-horizontal-header .header-controls {
  grid-column: 3;
  align-self: flex-start;
}

.company-logo {
  max-width: 240px;
  max-height: 100px;
  object-fit: contain;
  margin-right: 0.75rem;
}

.logo-section {
  display: flex;
  flex-direction: row;
  align-items: center;
  gap: 1.5rem;
  position: relative;
  flex-shrink: 0;
  min-width: 0; /* Permite que se reduzca si es necesario */
}

.logo-left {
  display: flex;
  align-items: center;
  flex-shrink: 0;
}

.logo-right {
  display: flex;
  flex-direction: column;
  align-items: flex-start;
  gap: 0.5rem;
  flex: 1;
  min-width: 0;
}

.autopago-header.modo-horizontal-header .logo-right {
  gap: 0.25rem;
}

.logo-right-top {
  display: flex;
  align-items: center;
  gap: 1rem;
  width: 100%;
}

.logo-section h1 {
  margin: 0;
  font-size: 1.8rem;
  color: var(--color-primario, #DC2626); /* Color primario dinámico */
  font-weight: 900;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}

.autopago-header.modo-horizontal-header .logo-section h1 {
  font-size: 1.5rem;
  margin-bottom: 0;
}

.autopago-header.modo-horizontal-header .logo-right h1.logo {
  font-size: 1.4rem;
  margin: 0;
  line-height: 1.2;
}

.subtitle {
  margin: 0;
  color: #666;
  font-size: 0.9rem;
}

.cart-badge {
  position: relative;
  font-size: 1.5rem;
  cursor: pointer;
  width: 46px;
  height: 46px;
  padding: 0;
  background: var(--color-primario, #DC2626); /* Color primario dinámico */
  border-radius: 50%;
  display: inline-flex;
  align-items: center;
  justify-content: center;
  transition: transform 0.2s;
  box-shadow: 0 2px 8px var(--color-primario-rgb, 220, 38, 38, 0.3);
  flex-shrink: 0;
}

/* Carrito debajo del buscador en header horizontal */
.cart-badge-header {
  margin-top: 0.35rem;
  align-self: center;
  display: inline-flex;
  align-items: center;
  gap: 0.4rem;
}

.cart-label-header {
  font-size: 0.8rem;
  font-weight: 600;
  color: #444;
  white-space: nowrap;
}

.cart-badge:hover {
  transform: scale(1.1);
}

.badge-count {
  position: absolute;
  top: -8px;
  right: -8px;
  background: var(--color-secundario, #FBBF24);
  color: white;
  border-radius: 50%;
  width: 24px;
  height: 24px;
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 0.75rem;
  font-weight: bold;
}

/* Controles integrados en el header */
.header-controls {
  display: flex;
  align-items: center;
  gap: 0.75rem;
  flex: 1;
  max-width: 500px;
  margin: 0 auto;
}

.header-controls.header-controls-horizontal {
  flex-direction: column;
  align-items: flex-end;
  gap: 0.5rem;
  min-width: 200px;
  flex: 0 0 auto;
  max-width: none;
  margin: 0;
  align-self: flex-start;
}

.header-search-input {
  flex: 1;
  padding: 0.5rem 1rem;
  font-size: 0.9rem;
  border: 2px solid #e5e7eb;
  border-radius: 25px;
  background: #f8f9fa;
  outline: none;
  min-height: 36px;
  max-height: 36px;
  touch-action: manipulation;
  transition: all 0.2s;
}

.header-search-input:focus {
  border-color: var(--color-primario, #DC2626);
  background: white;
  box-shadow: 0 2px 8px var(--color-primario-rgb, 220, 38, 38, 0.2);
}

.header-columns-switch {
  display: flex;
  gap: 0.5rem;
  flex-shrink: 0;
}

.header-column-btn {
  width: 36px;
  height: 36px;
  border: 2px solid #e5e7eb;
  border-radius: 8px;
  background: #f8f9fa;
  cursor: pointer;
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 1rem;
  transition: all 0.2s;
  touch-action: manipulation;
  padding: 0;
}

.header-column-btn:hover {
  border-color: var(--color-primario, #DC2626);
  background: white;
  transform: scale(1.05);
}

.header-column-btn.active {
  background: var(--color-primario, #DC2626);
  border-color: var(--color-primario, #DC2626);
  color: white;
  box-shadow: 0 2px 8px var(--color-primario-rgb, 220, 38, 38, 0.3);
}

.header-config-btn {
  width: auto;
  height: 36px;
  padding: 0 0.75rem;
  border: 2px solid #e5e7eb;
  border-radius: 8px;
  background: #f8f9fa;
  color: #666;
  font-size: 0.85rem;
  cursor: pointer;
  display: flex;
  align-items: center;
  gap: 0.25rem;
  transition: all 0.2s ease;
}

.header-config-btn:hover {
  border-color: var(--color-primario, #DC2626);
  background: white;
  color: var(--color-primario, #DC2626);
  transform: scale(1.05);
}

/* Categorías */
.categories-section {
  display: flex;
  gap: 1rem;
  margin: 0 auto 2rem auto;
  max-width: 1400px;
  width: 100%;
  box-sizing: border-box;
  overflow-x: auto;
  overflow-y: hidden;
  padding: 1rem 1.5rem;
  padding-bottom: 0.5rem;
  scrollbar-width: thin;
  scrollbar-color: var(--color-primario, #DC2626) #f0f0f0;
  /* Scroll táctil suave */
  -webkit-overflow-scrolling: touch;
  scroll-behavior: smooth;
  /* Permitir scroll horizontal con gestos táctiles */
  touch-action: pan-x;
}

.categories-section::-webkit-scrollbar {
  height: 6px;
  display: block;
}

.categories-section::-webkit-scrollbar-track {
  background: #f0f0f0;
  border-radius: 10px;
}

.categories-section::-webkit-scrollbar-thumb {
  background: var(--color-primario, #DC2626); /* Color primario dinámico */
  border-radius: 10px;
}

.categories-section::-webkit-scrollbar-thumb:hover {
  background: var(--color-primario-dark, #B91C1C);
}

/* Búsqueda en el header (modo horizontal) - debajo del nombre */
.search-in-header {
  width: 100%;
  max-width: 100%;
}

.search-input-header {
  width: 100%;
  padding: 0.5rem 0.75rem;
  font-size: 0.9rem;
  border: 2px solid #e5e5e5;
  border-radius: 8px;
  background: #f9f9f9;
  transition: all 0.3s;
}

.autopago-header.modo-horizontal-header .search-input-header {
  padding: 0.35rem 0.5rem;
  font-size: 0.8rem;
}

.search-input-header:focus {
  outline: none;
  border-color: var(--color-primario, #DC2626);
  background: white;
  box-shadow: 0 0 0 3px rgba(220, 38, 38, 0.1);
}

/* Categorías en el header (modo horizontal) - Tercera columna con scroll */
.categories-in-header-wrapper {
  width: 100%;
  max-width: 100%;
  overflow: hidden;
  min-width: 0;
  flex-shrink: 0;
  display: flex;
  flex-direction: column;
}

.categories-in-header {
  display: flex;
  gap: 0.75rem;
  overflow-x: auto;
  overflow-y: hidden;
  padding: 0.25rem 0;
  scrollbar-width: thin;
  scrollbar-color: var(--color-primario, #DC2626) transparent;
  -webkit-overflow-scrolling: touch;
  scroll-behavior: smooth;
  touch-action: pan-x;
  width: 100%;
  max-width: 100%;
  flex: 1;
}

.categories-in-header::-webkit-scrollbar {
  height: 4px;
}

.categories-in-header::-webkit-scrollbar-track {
  background: transparent;
}

.categories-in-header::-webkit-scrollbar-thumb {
  background: var(--color-primario, #DC2626);
  border-radius: 2px;
}

.category-btn-header {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 0.25rem;
  padding: 0.5rem 0.75rem;
  border: none;
  border-radius: 10px;
  background: white;
  cursor: pointer;
  transition: all 0.3s;
  min-width: 80px;
  flex-shrink: 0;
  box-shadow: 0 1px 5px rgba(0, 0, 0, 0.1);
  position: relative;
}

.autopago-header.modo-horizontal-header .category-btn-header {
  padding: 0.4rem 0.6rem;
  min-width: 70px;
}

.category-btn-header:hover {
  transform: translateY(-2px);
  box-shadow: 0 3px 10px rgba(0, 0, 0, 0.15);
}

.category-btn-header.active {
  background: var(--color-primario, #DC2626);
  color: white;
  box-shadow: 0 3px 15px rgba(220, 38, 38, 0.3);
}

.category-img-header {
  width: 40px;
  height: 40px;
  object-fit: cover;
  border-radius: 8px;
}

.autopago-header.modo-horizontal-header .category-img-header {
  width: 35px;
  height: 35px;
}

.category-icon-header {
  font-size: 1.5rem;
}

.category-name-header {
  font-size: 0.7rem;
  font-weight: 600;
  text-align: center;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
  max-width: 80px;
}

.autopago-header.modo-horizontal-header .category-name-header {
  font-size: 0.65rem;
}

.edit-btn-small-header {
  position: absolute;
  top: 0.25rem;
  right: 0.25rem;
  background: var(--color-primario, #DC2626);
  color: white;
  border: none;
  border-radius: 50%;
  width: 20px;
  height: 20px;
  font-size: 0.6rem;
  cursor: pointer;
  display: flex;
  align-items: center;
  justify-content: center;
  box-shadow: 0 2px 5px rgba(0, 0, 0, 0.2);
  z-index: 10;
  transition: all 0.2s;
}

.edit-btn-small-header:hover {
  opacity: 0.9;
  transform: scale(1.1);
}

.category-btn {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 0.5rem;
  padding: 1rem 1.5rem;
  border: none;
  border-radius: 15px;
  background: white;
  cursor: pointer;
  transition: all 0.3s;
  min-width: 100px;
  min-height: 80px; /* Táctil-friendly */
  box-shadow: 0 2px 10px rgba(0, 0, 0, 0.1);
  touch-action: manipulation; /* Mejora respuesta táctil */
}

.category-btn:hover {
  transform: translateY(-5px);
  box-shadow: 0 5px 20px rgba(0, 0, 0, 0.2);
}

.category-btn.active {
  background: var(--color-primario, #DC2626); /* Color primario dinámico */
  color: white;
  transform: translateY(-5px);
  box-shadow: 0 4px 12px var(--color-primario-rgb, 220, 38, 38, 0.3);
}

.category-img {
  width: 40px;
  height: 40px;
  object-fit: contain;
  object-position: center;
  border-radius: 8px;
}

.category-icon {
  font-size: 2rem;
}

.category-name {
  font-size: 0.85rem;
  font-weight: 600;
}

/* Productos */
.products-section {
  display: grid;
  gap: 1.5rem;
  padding: 1.5rem;
  margin: 0 auto 2rem auto;
  max-width: 1400px; /* Limitar ancho máximo */
  width: 100%;
  box-sizing: border-box;
  /* Valor por defecto: 2 columnas - tamaño responsive de tarjetas */
  grid-template-columns: repeat(2, minmax(280px, 400px));
  justify-content: center; /* Centrar las columnas del grid */
  justify-items: center; /* Centrar el contenido dentro de cada celda */
  /* Hacer que solo los productos sean scrollables en vertical */
  max-height: calc(100vh - 260px); /* Header + búsqueda + categorías aprox */
  overflow-y: auto;
}

.products-section.columns-2 {
  grid-template-columns: repeat(2, minmax(280px, 400px)) !important;
  justify-content: center; /* Centrar las columnas del grid */
  justify-items: center; /* Centrar el contenido dentro de cada celda */
}

.products-section.columns-3 {
  grid-template-columns: repeat(3, minmax(280px, 400px)) !important;
  justify-content: center; /* Centrar las columnas del grid */
  justify-items: center; /* Centrar el contenido dentro de cada celda */
}

/* Modo horizontal: dos filas con scroll lateral */
.products-section.modo-horizontal {
  display: flex;
  flex-direction: column;
  gap: 1.5rem;
  max-height: calc(100vh - 260px);
  overflow-y: auto;
  padding: 1rem;
  max-width: 100%;
}

.products-section.modo-horizontal .horizontal-row {
  display: flex;
  flex-direction: row;
  gap: 1rem;
  overflow-x: auto;
  overflow-y: hidden;
  padding-bottom: 0.5rem;
  scrollbar-width: thin;
  scrollbar-color: var(--color-primario, #DC2626) transparent;
  min-height: 230px;
  align-items: center;
}

.products-section.modo-horizontal .horizontal-row::-webkit-scrollbar {
  height: 8px;
}

.products-section.modo-horizontal .horizontal-row::-webkit-scrollbar-track {
  background: transparent;
}

.products-section.modo-horizontal .horizontal-row::-webkit-scrollbar-thumb {
  background: var(--color-primario, #DC2626);
  border-radius: 4px;
}

.products-section.modo-horizontal .product-card {
  flex: 0 0 auto;
  min-width: 420px;
  max-width: 480px;
  width: 450px;
}

/* Tarjetas horizontales: imagen a la izquierda, texto a la derecha */
.product-card-horizontal {
  display: flex;
  padding: 0.35rem 0.5rem;
  align-items: center;
  height: 220px;
  max-height: 220px;
}

.product-horizontal-content {
  display: flex;
  flex-direction: row;
  align-items: stretch;
  gap: 0.75rem;
  width: 100%;
}

.product-image-horizontal {
  width: 70px;
  min-width: 70px;
  height: 70px;
  padding: 0.25rem;
}

.product-img-horizontal {
  width: 100%;
  height: 100%;
}

.product-info-horizontal {
  display: flex;
  flex-direction: column;
  justify-content: space-between;
  padding: 0;
}

.product-name-horizontal {
  font-size: 0.9rem;
  line-height: 1.1;
  max-height: 1.2em;
  overflow: hidden;
  text-overflow: ellipsis;
}

.product-description-horizontal {
  font-size: 0.75rem;
  max-height: 1.2em;
  overflow: hidden;
  text-overflow: ellipsis;
}

.product-footer-horizontal {
  display: flex;
  justify-content: space-between;
  align-items: center;
  gap: 0.35rem;
}

/* Botón más compacto en modo horizontal para reducir altura total */
.products-section.modo-horizontal .add-btn {
  min-height: 32px;
  padding: 0.2rem 0.6rem;
  font-size: 0.8rem;
}

.columns-switch {
  display: flex;
  gap: 0.5rem;
  background: white;
  padding: 0.25rem;
  border-radius: 8px;
  box-shadow: 0 2px 4px rgba(0,0,0,0.1);
}

.column-btn {
  padding: 0.5rem 0.75rem;
  border: none;
  background: transparent;
  cursor: pointer;
  border-radius: 6px;
  transition: all 0.2s;
  font-size: 1rem;
  color: #666;
  min-width: 44px; /* Táctil-friendly mínimo */
  min-height: 44px; /* Táctil-friendly mínimo */
  touch-action: manipulation; /* Mejora respuesta táctil */
}

.column-btn:hover {
  background: #f0f0f0;
}

.column-btn.active {
  background: #007bff;
  color: white;
}

/* Pantallas grandes táctiles (23" - 32") */
@media (min-width: 1920px) {
  .products-section {
    max-width: 1600px;
    gap: 2rem;
    padding: 2rem;
  }
  
  .products-section.columns-2 {
    grid-template-columns: repeat(2, minmax(400px, 450px)) !important;
    justify-content: center; /* Centrar las columnas del grid */
  }
  
  .products-section.columns-3 {
    grid-template-columns: repeat(3, minmax(400px, 450px)) !important;
    justify-content: center; /* Centrar las columnas del grid */
  }
  
  .product-card {
    max-width: 450px;
  }
  
  .product-card {
    font-size: 1.1rem;
  }
  
  .product-name {
    font-size: 1.5rem;
  }
  
  .product-price {
    font-size: 1.8rem;
  }
  
  .add-btn {
    padding: 1rem 2rem;
    font-size: 1.1rem;
    min-height: 50px; /* Táctil-friendly */
  }
  
  .category-btn {
    min-width: 120px;
    padding: 1.5rem 2rem;
    font-size: 1rem;
  }
  
  .search-input {
    padding: 1.25rem 2rem;
    font-size: 1.2rem;
    min-height: 50px; /* Táctil-friendly */
  }
}

/* Pantallas medianas táctiles (tablets grandes, 23") */
@media (min-width: 1024px) and (max-width: 1919px) {
  .products-section {
    max-width: 1400px;
  }
  
  .products-section.columns-2 {
    grid-template-columns: repeat(2, minmax(300px, 400px)) !important;
    justify-content: center; /* Centrar las columnas del grid */
  }
  
  .products-section.columns-3 {
    grid-template-columns: repeat(3, minmax(280px, 350px)) !important;
    justify-content: center; /* Centrar las columnas del grid */
  }
  
  .product-card {
    max-width: 400px;
  }
  
  .add-btn {
    min-height: 48px; /* Táctil-friendly */
  }
  
  .search-input {
    min-height: 48px; /* Táctil-friendly */
  }
}

/* Tablets y pantallas medianas */
@media (max-width: 1023px) and (min-width: 769px) {
  .products-section {
    padding: 1rem;
  }
  
  .products-section.columns-2,
  .products-section.columns-3 {
    grid-template-columns: repeat(2, minmax(250px, 350px)) !important;
    justify-content: center; /* Centrar las columnas del grid */
  }
  
  .product-card {
    max-width: 100%;
  }
  
  .add-btn {
    min-height: 48px; /* Táctil-friendly */
  }
}

/* Tablets pequeñas y móviles grandes */
@media (max-width: 768px) {
  .autopago-container {
    padding: 1rem;
  }
  
  .products-section {
    padding: 1rem;
    gap: 1rem;
  }
  
  .products-section.columns-2,
  .products-section.columns-3 {
    grid-template-columns: repeat(2, minmax(150px, 250px)) !important;
    justify-content: center; /* Centrar las columnas del grid */
  }
  
  .product-card {
    max-width: 100%;
  }
  
  .product-card {
    font-size: 0.95rem;
  }
  
  .product-name {
    font-size: 1.1rem;
  }
  
  .product-price {
    font-size: 1.3rem;
  }
  
  .add-btn {
    padding: 0.75rem 1.25rem;
    min-height: 44px; /* Táctil-friendly mínimo */
    font-size: 0.95rem;
  }
  
  .category-btn {
    min-width: 90px;
    padding: 0.75rem 1rem;
  }
  
  .search-input {
    padding: 0.875rem 1.25rem;
    font-size: 1rem;
    min-height: 44px; /* Táctil-friendly mínimo */
  }
}

/* Móviles pequeños */
@media (max-width: 480px) {
  .autopago-container {
    padding: 0.75rem;
  }
  
  .products-section {
    padding: 0.75rem;
    gap: 0.75rem;
  }
  
  .products-section.columns-2,
  .products-section.columns-3 {
    grid-template-columns: 1fr !important;
  }
  
  .product-card {
    max-width: 100%;
  }
  
  .autopago-header {
    padding: 0.75rem 1rem;
    gap: 0.5rem;
    flex-wrap: wrap;
  }
  
  .logo-section h1 {
    font-size: 1.4rem;
  }
  
  .company-logo {
    max-width: 200px;
    max-height: 80px;
  }
  
  .header-controls {
    max-width: 100%;
    gap: 0.5rem;
    order: 3;
    width: 100%;
    margin-top: 0.5rem;
  }
  
  .header-search-input {
    font-size: 0.85rem;
    padding: 0.4rem 0.8rem;
    min-height: 32px;
    max-height: 32px;
  }
  
  .header-column-btn {
    width: 32px;
    height: 32px;
    font-size: 0.9rem;
  }
  
  .cart-badge {
    width: 40px;
    height: 40px;
    font-size: 1.2rem;
  }
  
  .product-card {
    font-size: 0.9rem;
  }
  
  .product-name {
    font-size: 1rem;
  }
  
  .product-price {
    font-size: 1.2rem;
  }
  
  .add-btn {
    padding: 0.625rem 1rem;
    min-height: 44px; /* Táctil-friendly mínimo */
    font-size: 0.9rem;
  }
  
  .category-btn {
    min-width: 80px;
    padding: 0.625rem 0.875rem;
    font-size: 0.85rem;
  }
}

.product-card {
  background: white;
  border-radius: 16px;
  overflow: hidden;
  cursor: pointer;
  transition: all 0.3s ease;
  box-shadow: 0 2px 8px rgba(0, 0, 0, 0.08);
  border: 1px solid #e5e7eb;
  width: 100%;
  max-width: 400px; /* Tamaño máximo de tarjeta */
  box-sizing: border-box;
}

.product-card:hover {
  transform: translateY(-8px);
  box-shadow: 0 12px 24px rgba(0, 0, 0, 0.15);
  border-color: #DC2626;
}

.product-image {
  background: linear-gradient(135deg, #fef3c7 0%, #fde68a 50%, #fcd34d 100%); /* Gradiente amarillo suave tipo McDonald's - solo cuando no hay imagen */
  padding: 2rem;
  text-align: center;
  height: 180px;
  display: flex;
  align-items: center;
  justify-content: center;
  position: relative;
  overflow: hidden;
  width: 100%;
  box-sizing: border-box;
}

/* Cuando hay imagen, usar fondo blanco para que la transparencia PNG se vea correctamente */
.product-image.has-image {
  background: white;
}

.product-img {
  width: 100%;
  height: 100%;
  object-fit: contain; /* Cambiar de cover a contain para evitar deformaciones */
  object-position: center;
  /* Asegurar que las imágenes PNG transparentes se rendericen correctamente */
  mix-blend-mode: normal;
}

.edit-btn-overlay {
  position: absolute;
  top: 0;
  left: 0;
  width: 100%;
  height: 100%;
  background: var(--color-primario, #DC2626);
  opacity: 0.7;
  color: white;
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 2rem;
  cursor: pointer;
  opacity: 0;
  transition: opacity 0.3s ease;
  z-index: 5;
}

.product-image:hover .edit-btn-overlay {
  opacity: 0.7;
}

.edit-btn {
  position: absolute;
  top: 0.5rem;
  right: 0.5rem;
  background: var(--color-primario, #DC2626);
  color: white;
  border: none;
  border-radius: 8px;
  padding: 0.5rem 1rem;
  font-size: 0.85rem;
  cursor: pointer;
  display: flex;
  align-items: center;
  justify-content: center;
  box-shadow: 0 2px 5px rgba(0, 0, 0, 0.2);
  z-index: 10;
  transition: all 0.2s;
}

.edit-btn:hover {
  opacity: 0.9;
  transform: scale(1.05);
}

.edit-btn-small {
  position: absolute;
  top: 0.25rem;
  right: 0.25rem;
  background: var(--color-primario, #DC2626);
  color: white;
  border: none;
  border-radius: 50%;
  width: 30px;
  height: 30px;
  font-size: 0.8rem;
  cursor: pointer;
  display: flex;
  align-items: center;
  justify-content: center;
  box-shadow: 0 2px 5px rgba(0, 0, 0, 0.2);
  z-index: 10;
  transition: all 0.2s;
}

.edit-btn-small:hover {
  opacity: 0.9;
  transform: scale(1.1);
}

.logo-section.editable {
  cursor: pointer;
  position: relative;
}

.category-btn {
  position: relative;
}

.product-image::before {
  content: '';
  position: absolute;
  top: -50%;
  right: -50%;
  width: 200%;
  height: 200%;
  background: radial-gradient(circle, rgba(255, 255, 255, 0.3) 0%, transparent 70%);
  animation: shimmer 3s infinite;
}

@keyframes shimmer {
  0%, 100% { transform: translate(0, 0) rotate(0deg); }
  50% { transform: translate(-10px, -10px) rotate(5deg); }
}

.product-emoji {
  font-size: 5rem;
}

.product-info {
  padding: 1.5rem;
  cursor: pointer;
}

.product-name {
  margin: 0 0 0.5rem 0;
  font-size: 1.3rem;
  color: #333;
  font-weight: 700;
}

.product-description {
  margin: 0 0 1rem 0;
  color: #666;
  font-size: 0.9rem;
}

.product-footer {
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.product-price {
  font-size: 1.5rem;
  font-weight: 900;
  color: #DC2626; /* Rojo tipo McDonald's más suave */
  cursor: pointer;
  transition: transform 0.2s;
}

.product-price:hover {
  transform: scale(1.05);
}

.add-btn {
  background: var(--color-secundario, #FBBF24); /* Color secundario dinámico */
  color: #333;
  border: none;
  padding: 0.75rem 1.5rem;
  border-radius: 50px;
  font-weight: 700;
  cursor: pointer;
  transition: all 0.2s;
  box-shadow: 0 2px 8px rgba(251, 191, 36, 0.3);
  min-height: 44px; /* Táctil-friendly mínimo */
  min-width: 120px; /* Táctil-friendly mínimo */
  touch-action: manipulation; /* Mejora respuesta táctil */
}

.add-btn:hover {
  background: var(--color-secundario-dark, #F59E0B); /* Amarillo más oscuro al hover */
  transform: scale(1.05);
  box-shadow: 0 4px 12px rgba(251, 191, 36, 0.4);
}

/* Carrito */
.cart-overlay {
  position: fixed;
  top: 0;
  left: 0;
  right: 0;
  bottom: 0;
  background: rgba(0, 0, 0, 0.5);
  z-index: 1000;
  display: flex;
  justify-content: flex-end;
  animation: fadeIn 0.3s;
}

@keyframes fadeIn {
  from { opacity: 0; }
  to { opacity: 1; }
}

.cart-sidebar {
  width: 100%;
  max-width: 450px;
  background: white;
  height: 100vh;
  overflow: hidden; /* Sin scroll general, solo en items */
  animation: slideIn 0.3s;
  display: flex;
  flex-direction: column;
}

@keyframes slideIn {
  from { transform: translateX(100%); }
  to { transform: translateX(0); }
}

.cart-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 2rem;
  border-bottom: 2px solid #f0f0f0;
}

.cart-header h2 {
  margin: 0;
  font-size: 1.8rem;
  color: #333;
}

.close-btn {
  background: #f0f0f0;
  border: none;
  width: 40px;
  height: 40px;
  border-radius: 50%;
  cursor: pointer;
  font-size: 1.2rem;
  transition: all 0.2s;
}

.close-btn:hover {
  background: var(--color-primario, #DC2626); /* Color primario dinámico */
  color: white;
}

/* Footer superior con total y botones */
.cart-footer-top {
  padding: 1.5rem;
  border-bottom: 2px solid #f0f0f0;
  background: #f9f9f9;
  flex-shrink: 0; /* No se encoge */
}

.cart-actions-top {
  display: flex;
  gap: 1rem;
  margin-top: 1rem;
}

.add-separator-btn {
  flex: 1;
  padding: 1rem;
  background: #e5e7eb;
  border: 2px solid #d1d5db;
  border-radius: 10px;
  font-size: 1rem;
  font-weight: 600;
  color: #374151;
  cursor: pointer;
  transition: all 0.2s;
}

.add-separator-btn:hover {
  background: #d1d5db;
  border-color: #9ca3af;
}

.checkout-btn {
  flex: 2;
  padding: 1rem 2rem;
  background: var(--color-primario, #DC2626);
  color: white;
  border: none;
  border-radius: 10px;
  font-size: 1.2rem;
  font-weight: 700;
  cursor: pointer;
  transition: all 0.2s;
}

.checkout-btn:hover {
  background: var(--color-primario-dark, #B91C1C);
  transform: translateY(-2px);
  box-shadow: 0 4px 12px rgba(220, 38, 38, 0.3);
}

/* Contenedor scrolleable de items */
.cart-items-scrollable {
  flex: 1;
  overflow-y: auto;
  overflow-x: hidden;
  padding: 1rem;
  min-height: 0; /* Necesario para que flex funcione con overflow */
}

.cart-item {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 1rem;
  border-bottom: 1px solid #f0f0f0;
  gap: 1rem;
  cursor: move; /* Indicar que se puede arrastrar */
  transition: all 0.2s;
  background: white;
}

.cart-item:hover {
  background: #f9f9f9;
}

.cart-item.dragging {
  opacity: 0.5;
  transform: scale(0.95);
}

.cart-item.drag-over {
  border-top: 3px solid var(--color-primario, #DC2626);
}

/* Separador */
.cart-item-separator {
  padding: 1.5rem 1rem;
  background: #f3f4f6;
  border: 2px dashed #d1d5db;
  border-radius: 10px;
  margin: 0.5rem 0;
}

.separator-content {
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 1rem;
  width: 100%;
  position: relative;
}

.separator-line {
  flex: 1;
  height: 2px;
  background: #d1d5db;
}

.separator-text {
  font-size: 0.9rem;
  font-weight: 600;
  color: #6b7280;
  padding: 0 1rem;
}

.remove-separator-btn {
  position: absolute;
  right: 0;
  top: 50%;
  transform: translateY(-50%);
  background: #ef4444;
  color: white;
  border: none;
  width: 30px;
  height: 30px;
  border-radius: 50%;
  cursor: pointer;
  font-size: 1rem;
  display: flex;
  align-items: center;
  justify-content: center;
  transition: all 0.2s;
}

.remove-separator-btn:hover {
  background: #dc2626;
  transform: translateY(-50%) scale(1.1);
}

.cart-item-info {
  display: flex;
  align-items: center;
  gap: 1rem;
  flex: 1;
}

.cart-item-emoji {
  font-size: 2.5rem;
}

.cart-item-details h4 {
  margin: 0 0 0.25rem 0;
  font-size: 1.1rem;
  color: #333;
}

.cart-item-note {
  margin: 0.25rem 0;
  color: #3b82f6;
  font-size: 0.9rem;
  font-style: italic;
  font-weight: 500;
}

.cart-item-price {
  margin: 0;
  color: var(--color-primario, #DC2626);
  font-weight: 700;
  font-size: 1.1rem;
}

.cart-item-controls {
  display: flex;
  align-items: center;
  gap: 0.75rem;
}

.qty-btn {
  background: #f0f0f0;
  border: none;
  width: 35px;
  height: 35px;
  border-radius: 50%;
  cursor: pointer;
  font-size: 1.2rem;
  font-weight: 700;
  transition: all 0.2s;
}

.qty-btn:hover {
  background: var(--color-primario, #DC2626); /* Color primario dinámico */
  color: white;
}

.qty-value {
  font-size: 1.2rem;
  font-weight: 700;
  min-width: 30px;
  text-align: center;
  color: #333;
}

.remove-btn {
  background: transparent;
  border: none;
  font-size: 1.5rem;
  cursor: pointer;
  padding: 0.5rem;
  transition: transform 0.2s;
}

.remove-btn:hover {
  transform: scale(1.2);
}

.note-btn {
  background: transparent;
  border: 2px solid #e5e7eb;
  font-size: 1.3rem;
  cursor: pointer;
  padding: 0.5rem;
  border-radius: 8px;
  transition: all 0.2s;
  min-width: 40px;
  height: 40px;
  display: flex;
  align-items: center;
  justify-content: center;
}

.note-btn:hover {
  background: #f3f4f6;
  border-color: var(--color-primario, #DC2626);
  transform: scale(1.1);
}

.note-btn.has-note {
  background: #dbeafe;
  border-color: #3b82f6;
  color: #1e40af;
}

.note-textarea {
  resize: vertical;
  min-height: 100px;
  font-family: inherit;
}

.empty-cart {
  flex: 1;
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  color: #999;
}

.empty-emoji {
  font-size: 5rem;
  margin-top: 1rem;
}

.cart-footer {
  padding: 1.5rem;
  border-top: 2px solid #f0f0f0;
  background: #f9f9f9;
  flex-shrink: 0; /* No se encoge */
}

.cart-totals {
  margin-bottom: 1.5rem;
}

.total-line {
  display: flex;
  justify-content: space-between;
  padding: 0.5rem 0;
  font-size: 1rem;
  color: #666;
}

.total-final {
  font-size: 1.5rem;
  font-weight: 900;
  color: #333;
  border-top: 2px solid #ddd;
  padding-top: 1rem;
  margin-top: 0.5rem;
}

.checkout-btn {
  width: 100%;
  background: var(--color-primario, #DC2626); /* Color primario dinámico */
  color: white;
  border: none;
  padding: 1.25rem;
  border-radius: 15px;
  font-size: 1.2rem;
  font-weight: 700;
  cursor: pointer;
  transition: all 0.3s;
  box-shadow: 0 4px 15px rgba(255, 107, 107, 0.3);
}

.checkout-btn:hover {
  background: #ff5252;
  transform: translateY(-2px);
  box-shadow: 0 6px 20px rgba(255, 107, 107, 0.4);
}

/* Modales */
.modal-overlay {
  position: fixed;
  top: 0;
  left: 0;
  right: 0;
  bottom: 0;
  background: rgba(0, 0, 0, 0.7);
  z-index: 2000;
  display: flex;
  align-items: center;
  justify-content: center;
  animation: fadeIn 0.3s;
}

.modal-content {
  background: white;
  border-radius: 25px;
  padding: 2rem;
  max-width: 700px;
  width: 90%;
  max-height: 90vh;
  overflow-y: auto;
  text-align: center;
  animation: slideUp 0.3s;
  display: flex;
  flex-direction: column;
}

@keyframes slideUp {
  from {
    transform: translateY(50px);
    opacity: 0;
  }
  to {
    transform: translateY(0);
    opacity: 1;
  }
}

.modal-title {
  font-size: 1.75rem;
  color: #333;
  margin: 0 0 1.5rem 0;
  font-weight: 700;
  flex-shrink: 0;
}

.modal-options {
  display: flex;
  gap: 1.5rem;
  justify-content: center;
  flex-wrap: wrap;
}

.option-btn {
  flex: 1;
  min-width: 200px;
  padding: 2rem;
  border: 3px solid #f0f0f0;
  border-radius: 20px;
  background: white;
  cursor: pointer;
  transition: all 0.3s;
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 1rem;
}

.option-btn:hover {
  border-color: var(--color-primario, #DC2626);
  transform: translateY(-5px);
  box-shadow: 0 10px 30px var(--color-primario-rgb, 220, 38, 38, 0.2);
}

.option-btn.active {
  border-color: var(--color-primario, #DC2626);
  background: #fff5f5;
}

.option-icon {
  font-size: 4rem;
}

.option-label {
  font-size: 1.3rem;
  font-weight: 700;
  color: #333;
}

/* Formulario de factura */
.invoice-modal {
  max-width: 700px;
  width: 90%;
  text-align: left;
  padding: 2rem 2.5rem;
  max-height: 90vh;
  overflow-y: auto;
}

.invoice-form {
  margin-top: 1.5rem;
  padding-top: 1.5rem;
  border-top: 2px solid #f0f0f0;
  flex: 1;
  overflow-y: auto;
}

.form-group {
  margin-bottom: 1.25rem;
}

.form-group label {
  display: block;
  margin-bottom: 0.5rem;
  font-weight: 600;
  color: #333;
  font-size: 1rem;
}

.radio-group {
  display: flex;
  gap: 1rem;
  margin-bottom: 1rem;
}

.radio-label {
  display: flex;
  align-items: center;
  gap: 0.5rem;
  padding: 0.75rem 1.5rem;
  border: 2px solid #f0f0f0;
  border-radius: 10px;
  cursor: pointer;
  transition: all 0.2s;
  flex: 1;
}

.radio-label:hover {
  border-color: var(--color-primario, #DC2626);
  background: #fff5f5;
}

.radio-label input[type="radio"] {
  margin: 0;
  cursor: pointer;
}

.radio-label input[type="radio"]:checked + span,
.radio-label:has(input[type="radio"]:checked) {
  border-color: var(--color-primario, #DC2626);
  background: #fff5f5;
}

.form-input {
  width: 100%;
  padding: 1.25rem; /* Más grande */
  border: 3px solid #f0f0f0; /* Más grueso */
  border-radius: 10px;
  font-size: 1.2rem; /* Más grande */
  font-weight: 500; /* Más grueso */
  color: #333; /* Negro */
  transition: all 0.2s;
  box-sizing: border-box;
}

.form-input:focus {
  outline: none;
  border-color: #333; /* Negro en lugar de color primario */
  box-shadow: 0 0 0 3px rgba(51, 51, 51, 0.1); /* Negro con transparencia */
  color: #333; /* Negro */
}

/* Inputs de nombre, teléfono, email en modal de completar datos - más grandes y gruesos */
.invoice-modal .form-group .form-input {
  padding: 1.5rem; /* Aún más grande para estos inputs */
  font-size: 1.3rem; /* Más grande */
  font-weight: 600; /* Más grueso */
  border-width: 3px; /* Más grueso */
}

/* Estilos para display de mesa grande */
.mesa-display {
  width: 100%;
  min-height: 120px;
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 4rem;
  font-weight: bold;
  color: #999;
  background: #f9f9f9;
  border: 3px dashed #ddd;
  border-radius: 15px;
  margin-bottom: 1rem;
  transition: all 0.3s;
  letter-spacing: 0.2em;
}

.mesa-display.has-value {
  color: var(--color-primario, #DC2626);
  background: #fff5f5;
  border-color: var(--color-primario, #DC2626);
  border-style: solid;
}

.mesa-input-hidden {
  position: absolute;
  opacity: 0;
  pointer-events: auto; /* Permitir que sea clickeable aunque esté oculto */
  width: 1px;
  height: 1px;
  z-index: -1; /* Detrás del display */
}

.mesa-display {
  cursor: pointer; /* Mostrar que es clickeable */
  user-select: none; /* No seleccionar texto */
}

/* Estilos para display de teléfono (igual que mesa) */
.telefono-display {
  width: 100%;
  min-height: 120px;
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 4rem;
  font-weight: bold;
  color: #999;
  background: #f9f9f9;
  border: 3px dashed #ddd;
  border-radius: 15px;
  margin-bottom: 1rem;
  transition: all 0.3s;
  letter-spacing: 0.2em;
}

.telefono-display.has-value {
  color: #333; /* Negro en lugar de verde/rojo */
  background: #f9f9f9;
  border-color: #333; /* Negro en lugar de verde/rojo */
  border-style: solid;
}

.telefono-input-hidden {
  position: absolute;
  opacity: 0;
  pointer-events: auto; /* Permitir que sea clickeable aunque esté oculto */
  width: 1px;
  height: 1px;
  z-index: -1; /* Detrás del display */
}

.telefono-display {
  cursor: pointer; /* Mostrar que es clickeable */
  user-select: none; /* No seleccionar texto */
}

/* Estilos para display de contraseña (similar a teléfono pero más pequeño) */
.password-display {
  width: 100%;
  min-height: 80px;
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 2.5rem;
  font-weight: bold;
  color: #999;
  background: #f9f9f9;
  border: 3px dashed #ddd;
  border-radius: 15px;
  margin-bottom: 1rem;
  transition: all 0.3s;
  letter-spacing: 0.3em;
  cursor: pointer;
  user-select: none;
}

.password-display.has-value {
  color: #333;
  background: #f9f9f9;
  border-color: #333;
  border-style: solid;
}

.password-input-hidden {
  position: absolute;
  opacity: 0;
  pointer-events: auto;
  width: 1px;
  height: 1px;
  z-index: -1;
}

.color-input {
  height: 50px;
  padding: 0.25rem;
  width: 100%;
  border: 2px solid var(--color-primario, #DC2626);
  border-radius: 8px;
  cursor: pointer;
}

.color-preview {
  display: inline-block;
  width: 30px;
  height: 30px;
  border-radius: 4px;
  border: 2px solid #ddd;
  margin-left: 0.5rem;
  vertical-align: middle;
}

.payment-options {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(150px, 1fr));
  gap: 1rem;
  margin: 1.5rem 0;
}

.payment-option-btn {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  padding: 1.5rem;
  border: 2px solid #e5e7eb;
  border-radius: 12px;
  background: white;
  cursor: pointer;
  transition: all 0.3s;
  min-height: 120px;
}

.payment-option-btn:hover {
  border-color: #3b82f6;
  background: #eff6ff;
  transform: translateY(-2px);
  box-shadow: 0 4px 12px rgba(59, 130, 246, 0.2);
}

.payment-option-btn.active {
  border-color: #3b82f6;
  background: #dbeafe;
  box-shadow: 0 4px 12px rgba(59, 130, 246, 0.3);
}

.payment-icon {
  font-size: 2.5rem;
  margin-bottom: 0.5rem;
}

.payment-label {
  font-size: 0.9rem;
  font-weight: 600;
  color: #1f2937;
  text-align: center;
}

.form-help-text {
  font-size: 0.85rem;
  color: #6b7280;
  margin-top: 0.25rem;
  margin-bottom: 0.5rem;
}

.button-group {
  display: flex;
  flex-direction: column;
  gap: 0.75rem;
  margin-top: 1rem;
}

.continue-btn {
  width: 100%;
  background: var(--color-primario, #DC2626); /* Color primario dinámico */
  color: white;
  border: none;
  padding: 1.25rem;
  border-radius: 15px;
  font-size: 1.2rem;
  font-weight: 700;
  cursor: pointer;
  transition: all 0.3s;
  box-shadow: 0 4px 15px rgba(255, 107, 107, 0.3);
  flex-shrink: 0;
}

.continue-btn:hover:not(:disabled) {
  background: #ff5252;
  transform: translateY(-2px);
  box-shadow: 0 6px 20px rgba(255, 107, 107, 0.4);
}

.cancel-btn {
  width: 100%;
  background: #f0f0f0;
  color: #666;
  border: none;
  padding: 1rem;
  border-radius: 15px;
  font-size: 1.1rem;
  font-weight: 600;
  cursor: pointer;
  transition: all 0.3s;
}

.cancel-btn:hover {
  background: #e0e0e0;
  color: #333;
}

.back-btn {
  width: 100%;
  background: #f0f0f0;
  color: #666;
  border: none;
  padding: 1rem;
  border-radius: 15px;
  font-size: 1.1rem;
  font-weight: 600;
  cursor: pointer;
  transition: all 0.3s;
}

.back-btn:hover {
  background: #e0e0e0;
  color: #333;
}

.continue-btn:disabled {
  background: #ccc;
  cursor: not-allowed;
  box-shadow: none;
}

/* Modal de Pago */
.payment-modal {
  text-align: center;
  max-width: 900px;
  width: 90%;
  padding: 2.5rem 3rem;
  max-height: 85vh;
  display: flex;
  flex-direction: column;
  overflow-y: auto;
  overflow-x: hidden;
}

.payment-icon {
  font-size: 5rem;
  margin-bottom: 1rem;
  flex-shrink: 0;
}

.payment-message {
  font-size: 1.1rem;
  color: #666;
  margin: 1rem 0 1.5rem 0;
  line-height: 1.5;
  flex-shrink: 0;
}

.payment-amount {
  background: #f9f9f9;
  padding: 1.5rem;
  border-radius: 15px;
  margin: 1.5rem 0;
  flex-shrink: 0;
}

.amount-label {
  display: block;
  font-size: 1rem;
  color: #666;
  margin-bottom: 0.5rem;
}

.amount-value {
  display: block;
  font-size: 2.5rem;
  font-weight: 900;
  color: var(--color-primario, #DC2626);
}

.payment-loading {
  margin: 1.5rem 0;
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  min-height: 120px;
  flex-shrink: 0;
}

.spinner {
  width: 50px;
  height: 50px;
  border: 4px solid #f0f0f0;
  border-top-color: #DC2626; /* Rojo tipo McDonald's */
  border-radius: 50%;
  animation: spin 0.8s linear infinite;
  margin: 0 auto 1rem;
}

@keyframes spin {
  to { transform: rotate(360deg); }
}

.payment-loading p {
  color: #666;
  font-size: 1rem;
}

.cancel-payment-btn {
  margin-top: 1.5rem;
  background: transparent;
  color: #666;
  border: 2px solid #ddd;
  padding: 0.75rem 2rem;
  border-radius: 10px;
  font-size: 1rem;
  font-weight: 600;
  cursor: pointer;
  transition: all 0.2s;
  flex-shrink: 0;
  width: 100%;
  max-width: 300px;
  margin-left: auto;
  margin-right: auto;
}

.cancel-payment-btn:hover {
  border-color: var(--color-primario, #DC2626);
  color: var(--color-primario, #DC2626);
}

.required {
  color: var(--color-primario, #DC2626);
}

.validating-message {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 0.5rem;
  padding: 1rem;
  margin: 1rem 0;
  color: #666;
}

.spinner-small {
  width: 30px;
  height: 30px;
  border: 3px solid #f0f0f0;
  border-top-color: #DC2626; /* Rojo tipo McDonald's */
  border-radius: 50%;
  animation: spin 0.8s linear infinite;
}

.info-message {
  background: #d4edda;
  color: #155724;
  padding: 0.75rem 1rem;
  border-radius: 8px;
  margin-bottom: 1rem;
  font-size: 0.95rem;
  border: 1px solid #c3e6cb;
}

.order-type-badge {
  margin: 0.5rem 0 0 0;
  font-size: 0.85rem;
  color: #666;
  font-weight: 600;
}

.order-type-badge.clickable {
  cursor: pointer;
  padding: 0.25rem 0.5rem;
  border-radius: 6px;
  transition: all 0.2s ease;
  user-select: none;
}

.order-type-badge.clickable:hover {
  background: rgba(0, 0, 0, 0.05);
  color: var(--color-primario, #DC2626);
  transform: scale(1.05);
}

.order-type-badge.clickable:active {
  transform: scale(0.98);
}

.order-type-badges {
  display: flex;
  flex-direction: column;
  gap: 0.5rem;
  align-items: flex-start;
}

.mesa-badge {
  font-size: 0.8rem;
  color: #555;
}

/* Responsive adicional para modales y otros elementos */
@media (max-width: 768px) {
  .autopago-container {
    padding: 1rem;
  }

  .cart-sidebar {
    max-width: 100%;
  }

  .modal-content {
    padding: 1.5rem;
    max-height: 95vh;
  }
  
  .invoice-modal {
    padding: 1.5rem;
    max-height: 95vh;
  }
  
  .payment-modal {
    padding: 1.5rem;
    max-height: 95vh;
    width: 95%;
    max-width: 95%;
  }
  
  .payment-loading {
    min-height: 100px;
  }
  
  .cancel-payment-btn {
    max-width: 100%;
  }
  
  .modal-title {
    font-size: 1.5rem;
    margin-bottom: 1rem;
  }

  .modal-options {
    flex-direction: column;
  }

  .option-btn {
    min-width: 100%;
  }

  .radio-group {
    flex-direction: column;
  }
  
  .form-group {
    margin-bottom: 1rem;
  }
  
  .keyboard-mode-selector {
    top: 5px;
    right: 5px;
    padding: 0.5rem;
    font-size: 0.75rem;
  }
  
  .keyboard-mode-selector label {
    flex-direction: column;
    gap: 0.25rem;
  }
  
  .keyboard-mode-selector select {
    width: 100%;
  }
}

/* Teclado Virtual Personalizado */
.virtual-keyboard-overlay {
  position: fixed;
  top: 0;
  left: 0;
  right: 0;
  bottom: 0;
  background: rgba(0, 0, 0, 0.5);
  z-index: 3000;
  display: flex;
  align-items: flex-end;
  justify-content: center;
  animation: fadeIn 0.3s;
}

.virtual-keyboard {
  background: white;
  width: 100%;
  max-width: 800px;
  border-radius: 20px 20px 0 0;
  box-shadow: 0 -4px 20px rgba(0, 0, 0, 0.2);
  animation: slideUpKeyboard 0.3s;
  max-height: 50vh;
  display: flex;
  flex-direction: column;
}

@keyframes slideUpKeyboard {
  from {
    transform: translateY(100%);
  }
  to {
    transform: translateY(0);
  }
}

.virtual-keyboard-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 1rem 1.5rem;
  border-bottom: 2px solid #f0f0f0;
  font-weight: 600;
  color: #333;
}

.close-keyboard-btn {
  background: #f0f0f0;
  border: none;
  width: 32px;
  height: 32px;
  border-radius: 50%;
  cursor: pointer;
  font-size: 1.2rem;
  transition: all 0.2s;
}

.close-keyboard-btn:hover {
  background: var(--color-primario, #DC2626); /* Color primario dinámico */
  color: white;
}

.virtual-keyboard-body {
  padding: 1rem;
  overflow-y: auto;
  flex: 1;
}

.keyboard-row {
  display: flex;
  gap: 0.5rem;
  margin-bottom: 0.5rem;
  justify-content: center;
}

.keyboard-key {
  flex: 1;
  min-width: 50px;
  height: 50px;
  background: #f0f0f0;
  border: 2px solid #ddd;
  border-radius: 8px;
  font-size: 1.1rem;
  font-weight: 600;
  color: #333;
  cursor: pointer;
  transition: all 0.2s;
  user-select: none;
}

.keyboard-key:hover {
  background: var(--color-primario, #DC2626); /* Color primario dinámico */
  color: white;
  border-color: var(--color-primario, #DC2626);
  transform: scale(1.05);
}

.keyboard-key:active {
  transform: scale(0.95);
}

.keyboard-key-backspace {
  background: var(--color-primario, #DC2626); /* Color primario dinámico */
  color: white;
  border-color: var(--color-primario, #DC2626);
}

.keyboard-key-shift {
  background: #e5e7eb;
  font-weight: bold;
}

.keyboard-key-shift.active {
  background: var(--color-primario, #DC2626);
  color: white;
  border-color: var(--color-primario, #DC2626);
}

.keyboard-key-space {
  flex: 3;
  min-width: 150px;
}

.keyboard-numeric .keyboard-key {
  flex: 1;
  min-width: 80px;
  height: 60px;
  font-size: 1.5rem;
}

@media (max-width: 768px) {
  .virtual-keyboard {
    max-height: 60vh;
  }
  
  .keyboard-key {
    min-width: 45px;
    height: 45px;
    font-size: 1rem;
  }
  
  .keyboard-numeric .keyboard-key {
    min-width: 70px;
    height: 55px;
  }
}

/* Modal de Vista de Producto */
.product-view-overlay {
  background: rgba(0, 0, 0, 0.85);
  z-index: 3000;
}

.product-view-modal {
  max-width: 900px;
  width: 95%;
  max-height: 90vh;
  padding: 0;
  overflow: hidden;
  position: relative;
}

.close-product-view {
  position: absolute;
  top: 1rem;
  right: 1rem;
  background: rgba(0, 0, 0, 0.7);
  color: white;
  border: none;
  border-radius: 50%;
  width: 40px;
  height: 40px;
  font-size: 1.5rem;
  cursor: pointer;
  z-index: 10;
  display: flex;
  align-items: center;
  justify-content: center;
  transition: all 0.2s;
}

.close-product-view:hover {
  background: rgba(0, 0, 0, 0.9);
  transform: scale(1.1);
}

.product-view-container {
  display: flex;
  flex-direction: row;
  height: 100%;
  max-height: 90vh;
}

.product-view-image-container {
  flex: 1.1;
  min-height: 400px;
  background: linear-gradient(135deg, var(--color-secundario-light, #fef3c7), var(--color-secundario-mid, #fde68a), var(--color-secundario-dark, #fcd34d));
  display: flex;
  align-items: center;
  justify-content: center;
  position: relative;
  overflow: hidden;
  perspective: 1000px;
}

/* Cuando hay imagen, usar fondo blanco para que la transparencia PNG se vea correctamente */
.product-view-image-container.has-image {
  background: white;
}

.product-view-image {
  max-width: 80%;
  max-height: 80%;
  object-fit: contain;
  animation: rotate3d 20s infinite linear;
  transform-style: preserve-3d;
  filter: drop-shadow(0 20px 40px rgba(0, 0, 0, 0.3));
  /* Asegurar que las imágenes PNG transparentes se rendericen correctamente */
  mix-blend-mode: normal;
}

/* Precio superpuesto bajo la imagen (sin texto 'Precio') */
.product-view-price-tag {
  position: absolute;
  bottom: 1.5rem;
  left: 50%;
  transform: translateX(-50%);
  background: rgba(0, 0, 0, 0.75);
  color: #fff;
  padding: 0.5rem 1.5rem;
  border-radius: 999px;
  font-size: 1.4rem;
  font-weight: 800;
  letter-spacing: 0.03em;
  box-shadow: 0 6px 20px rgba(0, 0, 0, 0.4);
}

.product-view-emoji {
  font-size: 8rem;
  animation: rotate3d 20s infinite linear;
}

@keyframes rotate3d {
  0% {
    transform: rotateY(0deg) rotateX(5deg);
  }
  25% {
    transform: rotateY(90deg) rotateX(0deg);
  }
  50% {
    transform: rotateY(180deg) rotateX(-5deg);
  }
  75% {
    transform: rotateY(270deg) rotateX(0deg);
  }
  100% {
    transform: rotateY(360deg) rotateX(5deg);
  }
}

.product-view-info {
  flex: 1;
  padding: 2rem;
  background: white;
  overflow-y: auto;
  max-height: 90vh;
  display: flex;
  flex-direction: column;
  justify-content: center;
}

.product-view-name {
  font-size: 2rem;
  color: var(--color-primario, #DC2626);
  margin: 0 0 0.5rem 0;
  font-weight: 900;
}

.product-view-description {
  color: #666;
  font-size: 1.1rem;
  margin: 0 0 1.5rem 0;
}

.product-view-characteristics {
  margin: 1.5rem 0;
  padding: 1.5rem;
  background: var(--color-fondo, #f5f5f5);
  border-radius: 12px;
  border-left: 4px solid var(--color-primario, #DC2626);
}

.product-view-characteristics h3 {
  margin: 0 0 0.75rem 0;
  color: var(--color-primario, #DC2626);
  font-size: 1.2rem;
  font-weight: 700;
}

.product-view-characteristics p {
  margin: 0;
  color: #333;
  line-height: 1.6;
  white-space: pre-wrap;
}

.product-view-price {
  display: flex;
  align-items: center;
  gap: 1rem;
  margin: 1.5rem 0;
  padding: 1rem;
  background: var(--color-secundario-light, #fef3c7);
  border-radius: 12px;
}

.price-label {
  font-size: 1.1rem;
  color: #666;
  font-weight: 600;
}

.price-value {
  font-size: 2rem;
  color: var(--color-primario, #DC2626);
  font-weight: 900;
}

/* Responsive: en pantallas pequeñas, volver a columnas (imagen arriba, texto abajo) */
@media (max-width: 768px) {
  .product-view-container {
    flex-direction: column;
  }

  .product-view-image-container {
    min-height: 260px;
  }

  .product-view-info {
    max-height: 55vh;
  }
}

.add-to-cart-from-view {
  width: 100%;
  margin-top: 1rem;
  background: var(--color-secundario, #FBBF24);
  color: #333;
  font-weight: 700;
  font-size: 1.3rem;
  padding: 1.25rem;
}

.add-to-cart-from-view:hover {
  background: var(--color-secundario-dark, #F59E0B);
  transform: translateY(-2px);
  box-shadow: 0 6px 20px rgba(251, 191, 36, 0.4);
}

/* Protector de Pantalla (Screensaver) */
.screensaver-overlay {
  position: fixed;
  top: 0;
  left: 0;
  width: 100vw;
  height: 100vh;
  background: #000;
  z-index: 10000;
  display: flex;
  align-items: center;
  justify-content: center;
  cursor: pointer;
}

.screensaver-video-container {
  width: 100%;
  height: 100%;
  position: relative;
  display: flex;
  align-items: center;
  justify-content: center;
  overflow: hidden;
}

.screensaver-video {
  width: 100%;
  height: 100%;
  object-fit: cover; /* Por defecto, se ajustará según el formato */
  transition: object-fit 0.3s ease;
}

/* Cuando el video no llena la pantalla (formato diferente), agregar efecto blur de fondo */
.screensaver-video-container::before {
  content: '';
  position: absolute;
  top: 0;
  left: 0;
  width: 100%;
  height: 100%;
  background: #000;
  z-index: -1;
  filter: blur(20px);
  opacity: 0;
  transition: opacity 0.3s ease;
}

/* Clase para cuando el video usa contain (se aplica dinámicamente) */
.screensaver-video-container.video-contain::before {
  opacity: 1;
  background: #000;
}

.screensaver-placeholder {
  color: #666;
  font-size: 1.5rem;
  text-align: center;
}

/* Efecto de difuminado para videos que no llenan la pantalla */
.screensaver-video[style*="contain"] {
  filter: drop-shadow(0 0 30px rgba(0, 0, 0, 0.8));
}

/* Divider para sección de videos en el modal */
.form-section-divider {
  margin: 2rem 0 1rem 0;
  padding: 1rem 0;
  border-top: 2px solid #e5e7eb;
  border-bottom: 2px solid #e5e7eb;
}

.form-section-divider h3 {
  margin: 0;
  color: var(--color-primario, #DC2626);
  font-size: 1.2rem;
  font-weight: 700;
}

/* Modal de PDF de Factura */
.invoice-pdf-modal-overlay {
  z-index: 2500;
  display: flex;
  align-items: center;
  justify-content: center;
  padding: 2rem;
}

.invoice-pdf-modal {
  max-width: 90vw;
  max-height: 90vh;
  width: 120mm; /* Ancho similar al ticket de 80mm + márgenes */
  max-width: 120mm;
  display: flex;
  flex-direction: column;
  background: white;
  border-radius: 12px;
  box-shadow: 0 10px 40px rgba(0, 0, 0, 0.3);
  overflow: hidden;
}

.invoice-pdf-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 1rem 1.5rem;
  border-bottom: 2px solid #f0f0f0;
  background: var(--color-primario, #DC2626);
  color: white;
}

.invoice-pdf-header .modal-title {
  margin: 0;
  color: white;
  font-size: 1.2rem;
}

.header-actions {
  display: flex;
  align-items: center;
  gap: 0.5rem;
}

.btn-print-header {
  display: flex;
  align-items: center;
  gap: 0.75rem;
  padding: 0.875rem 1.5rem;
  background: rgba(255, 255, 255, 0.15);
  border: 2px solid rgba(255, 255, 255, 0.3);
  border-radius: 10px;
  color: white;
  font-size: 1rem;
  font-weight: 600;
  cursor: pointer;
  transition: all 0.3s ease;
  min-height: 48px;
  backdrop-filter: blur(10px);
}

.btn-print-header:hover:not(:disabled) {
  background: rgba(255, 255, 255, 0.25);
  border-color: rgba(255, 255, 255, 0.5);
  transform: translateY(-2px);
  box-shadow: 0 4px 12px rgba(0, 0, 0, 0.2);
}

/* Botón de cambio de usuario (discreto en esquina superior derecha) */
/* Botón de cerrar sesión (estilo igual al de datafono) */
.header-logout-btn {
  background: linear-gradient(135deg, var(--color-primario, #DC2626) 0%, #B91C1C 100%);
  color: white;
  border-color: var(--color-primario, #DC2626);
}

.header-logout-btn:hover {
  background: linear-gradient(135deg, #B91C1C 0%, #991B1B 100%);
  border-color: #991B1B;
  color: white;
}

/* Modal de cambio de usuario */
.user-switch-overlay {
  z-index: 10000;
  display: flex;
  align-items: center;
  justify-content: center;
  padding: 2rem;
  background: rgba(0, 0, 0, 0.5);
  backdrop-filter: blur(5px);
}

.user-switch-modal {
  max-width: 90vw;
  width: 100%;
  max-width: 400px;
  background: white;
  border-radius: 16px;
  box-shadow: 0 20px 60px rgba(0, 0, 0, 0.3);
  overflow: hidden;
}

.user-switch-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 1.5rem;
  border-bottom: 2px solid #f0f0f0;
  background: linear-gradient(135deg, var(--color-primario, #DC2626) 0%, #B91C1C 100%);
  color: white;
}

.user-switch-header .modal-title {
  margin: 0;
  color: white;
  font-size: 1.25rem;
  font-weight: 600;
}

.btn-close-modal {
  width: 36px;
  height: 36px;
  border-radius: 50%;
  background: rgba(255, 255, 255, 0.2);
  border: none;
  color: white;
  cursor: pointer;
  display: flex;
  align-items: center;
  justify-content: center;
  transition: all 0.2s ease;
  min-height: 48px;
  min-width: 48px;
}

.btn-close-modal:hover {
  background: rgba(255, 255, 255, 0.3);
  transform: scale(1.1);
}

.btn-close-modal svg {
  width: 20px;
  height: 20px;
}

.user-switch-content {
  padding: 2rem;
}

.switch-to-cajagc,
.switch-to-admin {
  text-align: center;
}

.switch-message {
  font-size: 1.1rem;
  color: #666;
  margin-bottom: 2rem;
}

.user-switch-form {
  display: flex;
  flex-direction: column;
  gap: 1.5rem;
}

.user-switch-form .form-group {
  display: flex;
  flex-direction: column;
  gap: 0.5rem;
}

.user-switch-form label {
  font-weight: 600;
  color: #333;
  font-size: 0.95rem;
}

.user-switch-form .form-input {
  width: 100%;
  padding: 1rem;
  border: 2px solid #e5e7eb;
  border-radius: 12px;
  font-size: 1.1rem;
  transition: all 0.2s ease;
  min-height: 56px;
  box-sizing: border-box;
}

.user-switch-form .form-input:focus {
  outline: none;
  border-color: var(--color-primario, #DC2626);
  box-shadow: 0 0 0 3px rgba(220, 38, 38, 0.1);
}

.user-switch-form .form-input:disabled {
  background: #f5f5f5;
  cursor: not-allowed;
}

.error-message {
  color: #DC2626;
  font-size: 0.9rem;
  text-align: center;
  padding: 0.75rem;
  background: #FEE2E2;
  border-radius: 8px;
  margin: 0;
}

.form-actions {
  display: flex;
  gap: 1rem;
  margin-top: 0.5rem;
}

.btn-cancel,
.btn-switch {
  flex: 1;
  padding: 1rem 1.5rem;
  border-radius: 12px;
  font-size: 1.1rem;
  font-weight: 600;
  cursor: pointer;
  transition: all 0.2s ease;
  min-height: 56px;
  border: 2px solid transparent;
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 0.5rem;
}

.btn-cancel {
  background: #f5f5f5;
  color: #666;
  border-color: #e5e7eb;
}

.btn-cancel:hover:not(:disabled) {
  background: #e5e7eb;
  transform: translateY(-2px);
  box-shadow: 0 4px 12px rgba(0, 0, 0, 0.1);
}

.btn-switch {
  background: linear-gradient(135deg, var(--color-primario, #DC2626) 0%, #B91C1C 100%);
  color: white;
}

.btn-switch:hover:not(:disabled) {
  transform: translateY(-2px);
  box-shadow: 0 6px 20px rgba(220, 38, 38, 0.3);
}

.btn-switch:disabled {
  opacity: 0.5;
  cursor: not-allowed;
}

.btn-switch-cajagc {
  background: linear-gradient(135deg, #666 0%, #444 100%);
}

.btn-switch-cajagc:hover:not(:disabled) {
  box-shadow: 0 6px 20px rgba(0, 0, 0, 0.2);
}

.spinner-small {
  width: 20px;
  height: 20px;
  border: 3px solid rgba(255, 255, 255, 0.3);
  border-top-color: white;
  border-radius: 50%;
  animation: spin 0.8s linear infinite;
}

@keyframes spin {
  to { transform: rotate(360deg); }
}

.btn-print-header:active:not(:disabled) {
  transform: translateY(0);
}

.btn-print-header:disabled {
  opacity: 0.5;
  cursor: not-allowed;
  background: rgba(255, 255, 255, 0.1);
}

.btn-print-header .btn-icon {
  width: 20px;
  height: 20px;
  flex-shrink: 0;
  stroke-width: 2.5;
}

.btn-print-header .btn-text {
  display: inline-block;
  white-space: nowrap;
}

/* Pestañas de PDF debajo del header */
.pdf-tabs {
  display: flex;
  gap: 0.5rem;
  padding: 0.75rem 1.5rem;
  border-bottom: 2px solid #f0f0f0;
  background: #f8f9fa;
}

.pdf-tab {
  padding: 0.75rem 1.5rem;
  border: none;
  background: transparent;
  color: #666;
  font-size: 1rem;
  font-weight: 500;
  cursor: pointer;
  border-radius: 8px 8px 0 0;
  transition: all 0.2s;
  position: relative;
  display: flex;
  align-items: center;
  gap: 0.5rem;
}

.pdf-tab:hover:not(:disabled) {
  background: rgba(0, 0, 0, 0.05);
  color: #333;
}

.pdf-tab.active {
  background: white;
  color: var(--color-primario, #DC2626);
  border-bottom: 3px solid var(--color-primario, #DC2626);
  font-weight: 600;
}

.pdf-tab:disabled {
  opacity: 0.5;
  cursor: not-allowed;
}

.pdf-tab .badge {
  font-size: 0.75rem;
  padding: 0.25rem 0.5rem;
  background: #ffc107;
  color: #000;
  border-radius: 12px;
  font-weight: 600;
}

/* Sección de botón de impresión - REMOVIDA, ahora está en el header */

.close-modal-btn {
  background: rgba(255, 255, 255, 0.2);
  border: none;
  width: 32px;
  height: 32px;
  border-radius: 50%;
  color: white;
  font-size: 1rem;
  cursor: pointer;
  transition: all 0.2s;
  display: flex;
  align-items: center;
  justify-content: center;
  flex-shrink: 0;
}

.close-modal-btn:hover {
  background: rgba(255, 255, 255, 0.3);
  transform: scale(1.1);
}

.invoice-pdf-content {
  flex: 1;
  overflow: auto;
  padding: 0.5rem 1rem;
  min-height: 400px;
  display: flex;
  align-items: flex-start;
  justify-content: center;
}

.pdf-loading {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  gap: 1rem;
  padding: 3rem;
}

.pdf-preview {
  width: 100%;
  height: 100%;
  min-height: 500px;
}

.pdf-iframe {
  width: 100%;
  height: 600px;
  border: 1px solid #ddd;
  border-radius: 8px;
  /* Ocultar controles de navegación del PDF viewer */
  -webkit-transform: scale(1);
  transform: scale(1);
}

.pdf-placeholder {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  gap: 1rem;
  padding: 3rem;
  text-align: center;
  color: #666;
}

.pdf-icon {
  font-size: 4rem;
}

/* Botones de acción flotantes - REMOVIDOS, ahora están en el header */

@media (max-width: 768px) {
  .invoice-pdf-modal {
    max-width: 95vw;
    max-height: 95vh;
    width: 100%;
  }
  
  .pdf-tabs {
    flex-wrap: wrap;
  }
  
  .invoice-pdf-header .header-actions {
    flex-wrap: wrap;
    gap: 0.5rem;
  }
  
  .btn-print-header {
    font-size: 0.9rem;
    padding: 0.75rem 1.25rem;
    min-height: 44px;
    gap: 0.5rem;
  }
  
  .btn-print-header .btn-icon {
    width: 18px;
    height: 18px;
  }
  
  .btn-print-header .btn-text {
    font-size: 0.9rem;
  }
  
  .invoice-pdf-content {
    min-height: 300px;
    padding: 1rem;
  }
  
  .pdf-iframe {
    height: 400px;
  }
  
  .invoice-action-buttons {
    flex-direction: column;
    gap: 0.75rem;
  }
  
  .action-btn {
    min-width: 100%;
    width: 100%;
  }
}

/* Estilos para notas rápidas */
.notas-rapidas-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(150px, 1fr));
  gap: 0.75rem;
  margin-top: 0.75rem;
}

.nota-rapida-btn {
  padding: 0.75rem 1rem;
  border: 2px solid #e0e0e0;
  border-radius: 8px;
  background: #ffffff;
  color: #333;
  font-size: 0.95rem;
  font-weight: 500;
  cursor: pointer;
  transition: all 0.2s ease;
  text-align: center;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}

.nota-rapida-btn:hover {
  border-color: var(--color-primario, #DC2626);
  background: #fff5f5;
  transform: translateY(-2px);
  box-shadow: 0 4px 12px rgba(220, 38, 38, 0.15);
}

.nota-rapida-btn.nota-rapida-activa {
  border-color: var(--color-primario, #DC2626);
  background: linear-gradient(135deg, var(--color-primario, #DC2626) 0%, #B91C1C 100%);
  color: white;
  font-weight: 600;
  box-shadow: 0 4px 12px rgba(220, 38, 38, 0.3);
}

.nota-rapida-btn.nota-rapida-activa:hover {
  background: linear-gradient(135deg, #B91C1C 0%, var(--color-primario, #DC2626) 100%);
  transform: translateY(-2px);
  box-shadow: 0 6px 16px rgba(220, 38, 38, 0.4);
}
</style>
