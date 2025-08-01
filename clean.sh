#!/usr/bin/env bash

SCRIPT_DIR=$(dirname "$0")

echo "cleaning: $SCRIPT_DIR"
rm -rf $SCRIPT_DIR/built/*
rm -rf $SCRIPT_DIR/dist/*

echo "cleaned out all built stuff"
