/**
 * Panel rendering for the InvenTree supplier cart plugin.
 *
 * InvenTree 1.x replaced the server-rendered PanelMixin with UserInterfaceMixin:
 * a panel is now a JavaScript module, dynamically imported by the front-end and
 * called as render(target, data). This file replaces the old Django templates
 * (supplier_panel/mouser.html and supplier_panel/add_supplierpart.html).
 *
 * `data` carries { user, model, id, instance, context }, where `context` is
 * whatever the Python side attached to the panel definition.
 */

const CART_COLUMNS = [
    { key: 'IPN', label: 'IPN' },
    { key: 'SKU', label: 'SKU' },
    { key: 'QuantityRequested', label: 'Required', align: 'right' },
    { key: 'QuantityAvailable', label: 'Available', align: 'right' },
    { key: '_status', label: 'Status' },
    { key: 'UnitPrice', label: 'Price', align: 'right', decimals: 4 },
    { key: 'ExtendedPrice', label: 'Total', align: 'right', decimals: 4 },
    { key: 'Error', label: 'Notes' },
];

function el(tag, props = {}, children = []) {
    const node = document.createElement(tag);
    for (const [k, v] of Object.entries(props)) {
        if (k === 'style') Object.assign(node.style, v);
        else if (k === 'text') node.textContent = v;
        else node.setAttribute(k, v);
    }
    for (const child of [].concat(children)) {
        if (child) node.appendChild(child);
    }
    return node;
}

function formatCell(item, col) {
    if (col.key === '_status') {
        // The old template compared requested against available. Keep that,
        // but treat a missing availability as unknown rather than a failure.
        const req = Number(item.QuantityRequested);
        const avail = Number(item.QuantityAvailable);
        if (!Number.isFinite(avail)) return { text: '?', tone: 'unknown' };
        return req <= avail
            ? { text: 'OK', tone: 'ok' }
            : { text: 'Short', tone: 'bad' };
    }
    const raw = item[col.key];
    if (raw === undefined || raw === null || raw === '') return { text: '' };
    if (col.decimals !== undefined && Number.isFinite(Number(raw))) {
        return { text: Number(raw).toFixed(col.decimals) };
    }
    return { text: String(raw) };
}

function buildTable(cart) {
    const items = (cart && cart.CartItems) || [];
    if (!items.length) {
        return el('p', { text: 'No cart items yet. Use "Transfer PO" to build one.' });
    }

    const thead = el('thead', {}, [
        el('tr', {}, CART_COLUMNS.map((c) =>
            el('th', {
                text: c.label,
                style: { textAlign: c.align || 'left', padding: '6px 10px' },
            })
        )),
    ]);

    const tbody = el('tbody', {}, items.map((item) =>
        el('tr', {}, CART_COLUMNS.map((col) => {
            const cell = formatCell(item, col);
            const td = el('td', {
                text: cell.text,
                style: { textAlign: col.align || 'left', padding: '6px 10px' },
            });
            if (cell.tone === 'ok') td.style.color = 'var(--mantine-color-green-6, green)';
            if (cell.tone === 'bad') td.style.color = 'var(--mantine-color-red-6, red)';
            return td;
        }))
    ));

    const total = Number(cart.MerchandiseTotal);
    const tfoot = el('tfoot', {}, [
        el('tr', {}, [
            el('td', { colspan: String(CART_COLUMNS.length - 3), text: '' }),
            el('td', { text: 'Total', style: { textAlign: 'right', fontWeight: '600', padding: '6px 10px' } }),
            el('td', { text: cart.currency_code || '', style: { textAlign: 'right', padding: '6px 10px' } }),
            el('td', {
                text: Number.isFinite(total) ? total.toFixed(4) : '',
                style: { textAlign: 'right', fontWeight: '600', padding: '6px 10px' },
            }),
            el('td', { text: '' }),
        ]),
    ]);

    return el('table', { style: { width: '100%', borderCollapse: 'collapse' } }, [thead, tbody, tfoot]);
}

/**
 * Panel shown on a PurchaseOrder detail page.
 */
export function renderPurchaseOrderPanel(target, data) {
    if (!target) {
        console.error('suppliercart: no target provided to renderPurchaseOrderPanel');
        return;
    }

    const ctx = (data && data.context) || {};
    const supplier = ctx.supplier || 'Supplier';
    const transferUrl = ctx.transfer_url;

    target.innerHTML = '';

    const button = el('button', {
        type: 'button',
        text: `Transfer PO to ${supplier}`,
        style: {
            padding: '6px 14px',
            cursor: 'pointer',
            borderRadius: '4px',
            border: '1px solid var(--mantine-color-gray-5, #ccc)',
        },
    });

    const status = el('div', { style: { margin: '10px 0', minHeight: '1.2em' } });
    const meta = el('div', { style: { margin: '6px 0', fontSize: '0.9em' } });
    const tableBox = el('div', {});

    function paint(cart, message, ok) {
        if (message) {
            status.textContent = message;
            status.style.color = ok
                ? 'var(--mantine-color-green-6, green)'
                : 'var(--mantine-color-red-6, red)';
        }
        meta.innerHTML = '';
        if (cart && (cart.cart_key || cart.cart_date)) {
            meta.appendChild(el('div', { text: `Cart key: ${cart.cart_key || '-'}` }));
            meta.appendChild(el('div', { text: `Cart date: ${cart.cart_date || '-'}` }));
        }
        tableBox.innerHTML = '';
        tableBox.appendChild(buildTable(cart));
    }

    button.addEventListener('click', async () => {
        if (!transferUrl) {
            paint(null, 'Plugin did not supply a transfer URL', false);
            return;
        }
        button.disabled = true;
        status.textContent = 'Transferring …';
        status.style.color = '';
        try {
            const response = await fetch(transferUrl, {
                credentials: 'same-origin',
                headers: { Accept: 'application/json' },
            });
            // A non-JSON body here means an auth redirect or a server error;
            // surface it rather than throwing an opaque parse error.
            const text = await response.text();
            let cart;
            try {
                cart = JSON.parse(text);
            } catch {
                paint(null, `Unexpected response (HTTP ${response.status})`, false);
                return;
            }
            const ok = cart.message === 'OK';
            paint(cart, ok ? 'Cart created' : cart.message || 'Transfer failed', ok);
        } catch (error) {
            paint(null, `Request failed: ${error}`, false);
        } finally {
            button.disabled = false;
        }
    });

    target.appendChild(button);
    target.appendChild(status);
    target.appendChild(meta);
    target.appendChild(tableBox);

    // Render whatever cart is already stored against this order.
    paint(ctx.cart || null, null, true);
}

/**
 * Panel shown on a Part detail page: create a supplier part from a SKU.
 */
export function renderPartPanel(target, data) {
    if (!target) {
        console.error('suppliercart: no target provided to renderPartPanel');
        return;
    }

    const ctx = (data && data.context) || {};
    const suppliers = ctx.suppliers || [];
    const addUrl = ctx.add_url;

    target.innerHTML = '';

    if (!suppliers.length) {
        target.appendChild(el('p', { text: 'No suppliers configured for this plugin.' }));
        return;
    }

    const select = el('select', { style: { padding: '5px', marginRight: '8px' } },
        suppliers.map((s) => el('option', { value: String(s.pk), text: s.name })));

    const sku = el('input', {
        type: 'text',
        placeholder: 'Supplier SKU',
        style: { padding: '5px', marginRight: '8px' },
    });

    const button = el('button', {
        type: 'button',
        text: 'Create supplier part',
        style: { padding: '5px 12px', cursor: 'pointer' },
    });

    const status = el('div', { style: { marginTop: '10px', minHeight: '1.2em' } });

    button.addEventListener('click', async () => {
        if (!sku.value.trim()) {
            status.textContent = 'Enter a SKU first';
            status.style.color = 'var(--mantine-color-red-6, red)';
            return;
        }
        button.disabled = true;
        status.textContent = 'Creating …';
        status.style.color = '';
        try {
            const response = await fetch(addUrl, {
                method: 'POST',
                credentials: 'same-origin',
                headers: {
                    'Content-Type': 'application/json',
                    'X-CSRFToken': getCsrfToken(),
                },
                body: JSON.stringify({
                    pk: ctx.part_pk,
                    supplier: Number(select.value),
                    sku: sku.value.trim(),
                }),
            });
            const result = await response.json();
            const ok = result.message === 'OK';
            status.textContent = ok ? 'Created' : result.message || 'Failed';
            status.style.color = ok
                ? 'var(--mantine-color-green-6, green)'
                : 'var(--mantine-color-red-6, red)';
        } catch (error) {
            status.textContent = `Request failed: ${error}`;
            status.style.color = 'var(--mantine-color-red-6, red)';
        } finally {
            button.disabled = false;
        }
    });

    target.appendChild(el('div', {}, [select, sku, button]));
    target.appendChild(status);
}

function getCsrfToken() {
    const match = document.cookie.match(/csrftoken=([^;]+)/);
    return match ? match[1] : '';
}
