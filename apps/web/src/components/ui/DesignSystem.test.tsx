import { render, screen } from '@testing-library/react';
import { describe, expect, it } from 'vitest';
import { Badge } from './Badge';
import { Button, Card } from './DesignSystem';

describe('luxury design-system primitives', () => {
  it('exposes reusable button variants without changing native button behavior', () => {
    render(
      <>
        <Button>Primary</Button>
        <Button variant="secondary">Secondary</Button>
        <Button variant="ghost">Ghost</Button>
        <Button variant="icon" aria-label="Open command palette">⌘</Button>
      </>,
    );

    expect(screen.getByRole('button', { name: 'Primary' }).classList.contains('button-primary')).toBe(true);
    expect(screen.getByRole('button', { name: 'Secondary' }).classList.contains('button-secondary')).toBe(true);
    expect(screen.getByRole('button', { name: 'Ghost' }).classList.contains('button-ghost')).toBe(true);
    expect(screen.getByRole('button', { name: 'Open command palette' }).classList.contains('icon-button')).toBe(true);
    expect(screen.getByRole('button', { name: 'Primary' }).querySelector('.button-content')?.textContent).toBe('Primary');
  });

  it('supports distinct surface hierarchy and semantic badge treatments', () => {
    render(
      <>
        <Card data-testid="base">Base</Card>
        <Card level="raised" data-testid="raised">Raised</Card>
        <Card level="feature" data-testid="feature">Feature</Card>
        <Card level="interactive" data-testid="interactive">Interactive</Card>
        <Badge variant="gold">Gold</Badge>
        <Badge variant="success">Success</Badge>
        <Badge variant="danger">Danger</Badge>
        <Badge variant="info">Info</Badge>
      </>,
    );

    expect(screen.getByTestId('base').classList.contains('surface-base')).toBe(true);
    expect(screen.getByTestId('raised').classList.contains('surface-raised')).toBe(true);
    expect(screen.getByTestId('feature').classList.contains('surface-feature')).toBe(true);
    expect(screen.getByTestId('interactive').classList.contains('surface-interactive')).toBe(true);
    expect(screen.getByText('Gold').classList.contains('badge-gold')).toBe(true);
    expect(screen.getByText('Success').classList.contains('badge-success')).toBe(true);
    expect(screen.getByText('Danger').classList.contains('badge-danger')).toBe(true);
    expect(screen.getByText('Info').classList.contains('badge-info')).toBe(true);
  });
});
