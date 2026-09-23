import { describe, expect, it } from 'vitest'
import { ZERO, add, compare, equals, fraction, multiply, subtract, sum, toNumber, toText } from './fraction'

describe('fraction', () => {
  it('reduces to lowest terms', () => {
    expect(fraction(6, 8)).toEqual([3, 4])
    expect(fraction(-2, 4)).toEqual([-1, 2])
  })

  it('normalises the sign onto the numerator', () => {
    expect(fraction(1, -2)).toEqual([-1, 2])
  })

  it('refuses a zero denominator', () => {
    expect(() => fraction(1, 0)).toThrow()
  })

  it('adds and subtracts exactly', () => {
    expect(add([1, 3], [1, 6])).toEqual([1, 2])
    expect(subtract([1, 2], [1, 3])).toEqual([1, 6])
    expect(multiply([2, 3], [3, 4])).toEqual([1, 2])
  })

  /**
   * The reason this module exists. In floating point the same sum is
   * 3.9999999999999996, and a bar of twelve triplet sixteenths would be
   * reported as not filling four beats.
   */
  it('sums twelve triplet sixteenths to exactly four beats', () => {
    const twelve = Array.from({ length: 12 }, () => fraction(1, 3))
    expect(sum(twelve)).toEqual([4, 1])
    expect(equals(sum(twelve), [4, 1])).toBe(true)
  })

  it('sums an empty list to zero', () => {
    expect(sum([])).toEqual(ZERO)
  })

  it('orders and prints', () => {
    expect(compare([1, 3], [1, 2])).toBeLessThan(0)
    expect(toNumber([3, 4])).toBe(0.75)
    expect(toText([4, 1])).toBe('4')
    expect(toText([3, 4])).toBe('3/4')
  })
})
