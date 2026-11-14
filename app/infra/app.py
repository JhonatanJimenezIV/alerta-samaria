#!/usr/bin/env python3
"""Punto de entrada del CDK App. Ejecutar con: bash scripts/deploy.sh (dentro de cdk-dev)."""
import aws_cdk as cdk
from stack import AlertaSamariaStack

app: cdk.App = cdk.App()
AlertaSamariaStack(
    app,
    "AlertaSamariaStack",
    env=cdk.Environment(account="000000000000", region="us-east-1"),  # cuenta dummy del emulador
)
app.synth()
