import type { InvenTreePluginContext } from '@inventreedb/ui';

type Supplier = {
  pk: number;
  name: string;
};

type ManufacturerPart = {
  pk: number;
  MPN: string;
};

type AddSupplierPartContext = {
  suppliers?: Supplier[];
  manufacturer_parts?: ManufacturerPart[];
  part_id?: number | string;
  add_supplierpart_url?: string;
};

function ensureStyles(): void {
  if (document.getElementById('suppliercart-add-part-style')) {
    return;
  }

  const style = document.createElement('style');
  style.id = 'suppliercart-add-part-style';
  style.textContent = `
    .suppliercart-wheel {
      border: 5px solid #f3f3f3;
      border-top: 5px solid #3498db;
      border-radius: 50%;
      width: 30px;
      height: 30px;
      animation: suppliercart-spin 2s linear infinite;
      visibility: hidden;
    }

    @keyframes suppliercart-spin {
      0% { transform: rotate(0deg); }
      100% { transform: rotate(360deg); }
    }
  `;

  document.head.appendChild(style);
}

function getCsrfToken(): string {
  const cookies = document.cookie.split(';').map((item) => item.trim());

  for (const cookie of cookies) {
    if (cookie.startsWith('csrftoken=')) {
      return decodeURIComponent(cookie.slice('csrftoken='.length));
    }
  }

  return '';
}

function setResult(target: HTMLElement, message: string): void {
  target.textContent = message;

  if (message === 'OK') {
    target.className = 'alert alert-block alert-success';
  } else {
    target.className = 'alert alert-block alert-danger';
  }
}

function renderOptions<T extends Record<string, string | number>>(
  items: T[],
  valueKey: keyof T,
  labelKey: keyof T
): string {
  return items
    .map(
      (item) =>
        `<option value="${String(item[valueKey])}">${String(item[labelKey])}</option>`
    )
    .join('');
}

export function renderAddSupplierPartPanel(
  target: HTMLElement | null,
  data: InvenTreePluginContext
): void {
  if (!target) {
    return;
  }

  ensureStyles();

  const panelContext =
    (data?.context as AddSupplierPartContext | undefined) ?? {};
  const suppliers = Array.isArray(panelContext.suppliers)
    ? panelContext.suppliers
    : [];
  const manufacturerParts = Array.isArray(panelContext.manufacturer_parts)
    ? panelContext.manufacturer_parts
    : [];

  const hasManufacturerPart = manufacturerParts.length > 0;

  target.innerHTML = `
    <div class="alert alert-block" id="suppliercart-add-result">&nbsp;</div>
    <div id="suppliercart-add-loader" class="suppliercart-wheel"></div>
    <table class="table table-condensed">
      <tbody>
        <tr>
          <td>Select Supplier</td>
          <td>
            <select id="suppliercart-supplier">
              ${renderOptions(suppliers, 'pk', 'name')}
            </select>
          </td>
        </tr>
        <tr>
          <td>
            ${hasManufacturerPart ? 'Select Manufacturer Part' : '<span style="color:red;">Part has no manufacturer part</span>'}
          </td>
          <td>
            <select id="suppliercart-manufacturer-part">
              ${renderOptions(manufacturerParts, 'pk', 'MPN')}
            </select>
          </td>
        </tr>
        <tr>
          <td>Exact supplier part number from suppliers WEB page</td>
          <td>
            <input id="suppliercart-sku" type="text" value="">
          </td>
        </tr>
        <tr>
          <td>Ignore MPN mismatch</td>
          <td>
            <input id="suppliercart-ignore-mpn" type="checkbox">
          </td>
        </tr>
      </tbody>
      <tfoot>
        <tr>
          <td>
            <button type="button" class="btn btn-dark" id="suppliercart-add-button" ${hasManufacturerPart ? '' : 'disabled'}>Add Part</button>
          </td>
          <td></td>
        </tr>
      </tfoot>
    </table>
  `;

  const resultNode = target.querySelector<HTMLElement>(
    '#suppliercart-add-result'
  );
  const loaderNode = target.querySelector<HTMLElement>(
    '#suppliercart-add-loader'
  );
  const addButton = target.querySelector<HTMLButtonElement>(
    '#suppliercart-add-button'
  );

  if (!resultNode || !loaderNode || !addButton) {
    return;
  }

  addButton.addEventListener('click', async () => {
    const skuNode = target.querySelector<HTMLInputElement>('#suppliercart-sku');
    const supplierNode = target.querySelector<HTMLSelectElement>(
      '#suppliercart-supplier'
    );
    const manufacturerPartNode = target.querySelector<HTMLSelectElement>(
      '#suppliercart-manufacturer-part'
    );
    const ignoreMpnNode = target.querySelector<HTMLInputElement>(
      '#suppliercart-ignore-mpn'
    );

    if (!skuNode || !supplierNode || !manufacturerPartNode || !ignoreMpnNode) {
      setResult(resultNode, 'Missing required fields');
      return;
    }

    if (!panelContext.add_supplierpart_url) {
      setResult(resultNode, 'Target URL is missing');
      return;
    }

    const payload = {
      sku: skuNode.value || '',
      supplier: Number(supplierNode.value),
      pk: Number(panelContext.part_id),
      mpart: Number(manufacturerPartNode.value),
      ignoreMPNCheck: Boolean(ignoreMpnNode.checked)
    };

    loaderNode.style.visibility = 'visible';

    try {
      const response = await fetch(panelContext.add_supplierpart_url, {
        method: 'POST',
        credentials: 'include',
        headers: {
          'Content-Type': 'application/json',
          'X-CSRFToken': getCsrfToken()
        },
        body: JSON.stringify(payload)
      });

      const responseData = (await response.json()) as { message?: string };
      setResult(resultNode, responseData.message || 'Error');
    } catch {
      setResult(resultNode, 'Request failed');
    } finally {
      loaderNode.style.visibility = 'hidden';
    }
  });
}
