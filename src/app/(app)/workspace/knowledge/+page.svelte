<script>
	import { onMount } from 'svelte';
	import { knowledge } from '$shared/stores';

	import { getKnowledgeBases } from '$api/knowledge';
	import Knowledge from '$features/workspace/Knowledge.svelte';

	onMount(async () => {
		await Promise.all([
			(async () => {
				knowledge.set(await getKnowledgeBases(localStorage.token));
			})()
		]);
	});
</script>

{#if $knowledge !== null}
	<Knowledge />
{/if}
