import stdlib/interval
import stdlib/assert

let a = interval(1.0, 2.0)
let b = interval(3.5, 4.0)
let c = a + b

assert.equal(c.lower, 4.5)
assert.equal(c.upper, 6.0)
