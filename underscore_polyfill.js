// Polyfill for _.contains which was deprecated and replaced with _.includes
if (typeof _ !== 'undefined' && !_.contains) {
    _.contains = _.includes;
}