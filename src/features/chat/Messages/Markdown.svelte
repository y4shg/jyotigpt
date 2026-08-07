<script>
	import { marked } from 'marked';
	import { replaceTokens, processResponseContent } from '$shared/utils';
	import { user } from '$shared/stores';

	import markedExtension from '$shared/utils/marked/extension';
	import markedKatexExtension from '$shared/utils/marked/katex-extension';

	import MarkdownTokens from './Markdown/MarkdownTokens.svelte';

	export let id = '';
	export let content;
	export let model = null;
	export let save = false;

	export let sourceIds = [];

	export let onUpdate = () => {};
	export let onCode = () => {};

	export let onSourceClick = () => {};
	export let onTaskClick = () => {};

	let tokens = [];

	const options = {
		throwOnError: false
	};

	marked.use(markedKatexExtension(options));
	marked.use(markedExtension(options));

	$: (async () => {
		if (content) {
			tokens = marked.lexer(
				replaceTokens(processResponseContent(content), sourceIds, model?.name, $user?.name)
			);
		}
	})();
</script>

{#key id}
	<MarkdownTokens {tokens} {id} {save} {onTaskClick} {onSourceClick} {onUpdate} {onCode} />
{/key}
