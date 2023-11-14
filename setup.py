# -*- coding: utf-8 -*-

import setuptools
from inventree_supplier_panel.version import PLUGIN_VERSION


with open('README.md', encoding='utf-8') as f:
    long_description = f.read()


setuptools.setup(
    name="inventree-supplier-panel",
    version=PLUGIN_VERSION,
    author="Michael Buchmann",
    author_email="michael@buchmann.ruhr",
    description="Syncronize a PO with a supplier online store",
    long_description=long_description,
    long_description_content_type='text/markdown',
    keywords="inventree supplier inventory store purchase order",
    url="https://github.com/SergeoLacruz/inventree-supplier-panel",
    license="MIT",
    packages=setuptools.find_packages(),
    setup_requires=[
        "wheel",
        "twine",
    ],
    python_requires=">=3.6",
    entry_points={
        "inventree_plugins": [
            "SupplierCartPanel = inventree_supplier_panel.supplier_panel:SupplierCartPanel"
        ]
    },
    include_package_data=True,
)
